import os
import gzip
import asyncio
from collections import OrderedDict
from wsgiref.handlers import format_date_time

MIMETYPES = OrderedDict({
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'json': 'application/json',
    'tif': 'image/tiff',
    '': 'text/plain',
})

def __readfile(path):
    with open(path, 'rb') as file:
        return file.read()

def __writefile(path, content):
    with open(path, 'wb') as file:
        file.write(content)

async def aioread(path, loop, executor):
    return await loop.run_in_executor(executor, __readfile, path)

async def aiowrite(path, content, loop, executor):
    await loop.run_in_executor(executor, __writefile, path, content)

def get_etag_from_file(timestamp, file):
    return str(round(100 * (timestamp % (3600 * 48)))) + ''.join(file.split(os.path.sep)[-3:])

def get_etag_from_args(*args):
    return ''.join([str(a) for a in args])

def get_headers(string):
    ext = string.split('.')[-1].lower()
    for key in MIMETYPES.keys():
        if key in ext:
            return {
                'Content-Type': MIMETYPES[ext],
                'Cache-Control': 'public',
            }

class Tile:
    '''
    Base class for tile handling.
    '''

    def __init__(self, *args):
        self.file, self.executor, compresslevel, *__ = args
        self.headers = {}
        self.respond = self.makerespond(compresslevel)

    async def read(self):
        loop = asyncio.get_event_loop()
        return await aioread(self.file, loop, self.executor)

    async def write(self, content):
        loop = asyncio.get_event_loop()
        dir = os.path.dirname(self.file)
        if not os.path.isdir(dir):
            os.makedirs(dir)
        await aiowrite(self.file, content, loop, self.executor)

    def makerespond(self, compresslevel):
        if 0 < compresslevel < 10:
            self.headers.update({
                'Content-Encoding': 'gzip',
                'Vary': 'Accept-Encoding',
            })
            def respond(content):
                content = gzip.compress(
                    content,
                    compresslevel = compresslevel
                )
                try:
                    self.headers['Content-Length']
                except KeyError:
                    self.headers.update({
                        'Content-Length': len(content)
                    })
                return 200, self.headers, content
        else:
            def respond(content):
                return 200, self.headers, content

        return respond

class FileTile(Tile):
    '''
    Extends Tile class to a callable object that calls self.modified on init.
    '''
    def __init__(self, *args):
        super(FileTile, self).__init__(path, executor, compresslevel)
        self.headers.update(get_headers(self.file))
        self.modified()

    async def modified(self):
        timestamp = os.path.getmtime(self.file)
        lastmod = format_date_time(timestamp)
        etag = get_etag_from_file(timestamp, self.file)
        self.headers.update({
            'Last-Modified': lastmod,
            'ETag': etag,
        })
        return lastmod, etag

    async def __call__(self):
        content = await self.read()
        return self.respond(content)

class ProxyTile(Tile):
    '''
    Extends Tile class to handle remote tile urls and cache content locally.
    '''

    def __init__(self, *args):
        path, executor, compresslevel, self.url, self.session, *__ = args
        super(ProxyTile, self).__init__(path, executor, compresslevel)
        self.headers.update(get_headers(self.url))
        self.proxypass = self.makepass()

    def makepass(self):
        if self.file is None:
            async def proxypass():
                async with self.session.get(self.url) as response:
                    if response.status == 404:
                        raise FileNotFoundError
                    return await response.read()
        else:
            async def proxypass():
                try:
                    content = await self.read()
                    return content
                except FileNotFoundError:
                    async with self.session.get(self.url) as response:
                        content = await response.read()
                    asyncio.ensure_future(self.write(content))
                    return content
        return proxypass

    async def __call__(self):
        content = await self.proxypass()
        return self.respond(content)

class LazyTile(Tile):
    '''
    Extends Tile class to handle tiles generated on demand.
    '''

    def __init__(self, *args):
        path, executor, compresslevel, *__, self.source, self.key = args
        super(LazyTile, self).__init__(path, executor, compresslevel)
        self.key = tuple(int(x) for x in self.key)
        self.headers.update(get_headers(self.source.format))
        self.lazypass = self.makepass()
        self.modified()

    async def modified(self):
        timestamp = await self.source.modified()
        lastmod = format_date_time(timestamp)
        etag = get_etag_from_args(timestamp, *self.key)
        self.headers.update({
            'Last-Modified': lastmod,
            'ETag': etag,
        })
        return lastmod, etag

    def makepass(self):
        if self.file is None:
            async def lazypass():
                return await self.source(*self.key)
        else:
            async def lazypass():
                try:
                    content = await self.read()
                    return content
                except FileNotFoundError:
                    content = await self.source(*self.key)
                    asyncio.ensure_future(self.write(content))
                    return content
        return lazypass

    async def __call__(self):
        content = await self.lazypass()
        return self.respond(content)
