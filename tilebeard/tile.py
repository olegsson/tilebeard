import os
import gzip
import asyncio
from wsgiref.handlers import format_date_time
import aiohttp

from .tbutils import TileNotFound

MIMETYPES = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'tif': 'image/tiff',
    'json': 'application/json',
    'geojson': 'application/json',
    'topojson': 'application/json',
    'mvt': 'application/x-protobuf',
    'pbf': 'application/x-protobuf',
}

TEXT_FORMATS = [
    'json',
    'geojson',
    'topojson',
]

DEFAULT_HEADERS = {
    'Cache-Control': 'public',
}


def __readfile(path, mode):
    with open(path, 'r'+mode) as file:
        return file.read()

def __writefile(path, content, mode):
    with open(path, 'w'+mode) as file:
        file.write(content)

def getmode(frmt):
    if frmt in TEXT_FORMATS:
        return ''
    return 'b'

async def aioread(path, loop, executor, mode):
    return await loop.run_in_executor(executor, __readfile, path, mode)

async def aiowrite(path, content, loop, executor, mode):
    await loop.run_in_executor(executor, __writefile, path, content, mode)

def get_etag_from_file(timestamp, file):
    return str(round(100 * (timestamp % (3600 * 48)))) + ''.join(file.split(os.path.sep)[-3:])

def get_etag_from_args(*args):
    return ''.join([str(a) for a in args])

def get_headers(string):
    ext = string.split('.')[-1].lower()
    return {
        'Content-Type': MIMETYPES[ext],
    }
    return headers, __getmode(ext)

class Tile:
    '''
    Base class for tile handling.
    '''

    def __init__(self, *args):
        self.file, self.format, self.executor, compresslevel, *__ = args
        self.headers = dict(DEFAULT_HEADERS)
        self.mode = getmode(self.format)
        self.respond = self.makerespond(compresslevel)

    async def read(self):
        loop = asyncio.get_event_loop()
        return await aioread(self.file, loop, self.executor, self.mode)

    async def write(self, content):
        loop = asyncio.get_event_loop()
        dir = os.path.dirname(self.file)
        try:
            os.makedirs(dir)
        except FileExistsError:
            pass
        await aiowrite(self.file, content, loop, self.executor, self.mode)

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
        super(FileTile, self).__init__(*args)
        self.headers.update(get_headers(self.file))
        asyncio.ensure_future(self.modified())

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
        path, frmt, executor, compresslevel, self.url, self.session, *__ = args
        super(ProxyTile, self).__init__(path, frmt, executor, compresslevel)
        self.headers.update(get_headers(self.url))
        self.proxypass = self.makepass()

    def makepass(self):
        if self.file is None:
            async def proxypass():
                async with self.session.get(self.url) as response:
                    if response.status == 404:
                        raise TileNotFound
                    return await response.read()
        else:
            async def proxypass():
                try:
                    content = await self.read()
                    return content
                except FileNotFoundError:
                    if self.session is None:
                        async with aiohttp.request('GET', self.url) as response:
                            content = await response.read()
                    else:
                        async with self.session.get(self.url) as response:
                            content = await response.read()
                    await self.write(content)
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
        path, frmt, executor, compresslevel, *__, self.source, self.key = args
        super(LazyTile, self).__init__(path, frmt, executor, compresslevel)
        self.key = tuple(int(x) for x in self.key)
        self.headers.update(get_headers(self.source.format))
        self.lazypass = self.makepass()
        asyncio.ensure_future(self.modified())

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
                    await self.write(content)
                    return content
        return lazypass

    async def __call__(self):
        content = await self.lazypass()
        return self.respond(content)
