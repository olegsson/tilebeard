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

def get_lastmod_etag(file):
    timestamp = os.path.getmtime(file)
    return (
        format_date_time(timestamp),
        str(round(100 * (timestamp % (3600 * 48)))) + ''.join(file.split(os.path.sep)[-3:])
    )

class Tile:
    '''
    Callable class for handling individual tiles.
    Stores filepath and headers, returns them on __call__.
    '''

    def __init__(self, *args):
        self.file, self.executor, compresslevel, *rest = args
        self.ext = self.file.split('.')[-1].lower()
        for ext in MIMETYPES.keys():
            try:
                if ext in self.ext:
                    self.headers = {
                        'Content-Type': MIMETYPES[ext],
                        'Cache-Control': 'public',
                    }
                    break
            except TypeError:
                pass

        self.respond = self.makerespond(compresslevel)
        if self.file is not None:
            self.modified()

    def modified(self):
        lastmod, etag = get_lastmod_etag(self.file)
        self.headers.update({
            'Last-Modified': lastmod,
            'ETag': etag
        })
        return lastmod, etag

    async def read(self):
        loop = asyncio.get_event_loop()
        return await aioread(self.file, loop, self.executor)

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

    async def __call__(self):
        content = await self.read()
        return self.respond(content)

class ProxyTile(Tile):
    '''
    Extends Tile class to handle remote tile urls and cache content locally.
    '''

    def __init__(self, *args):
        path, executor, compresslevel, self.url, self.session, *rest = args
        super(ProxyTile, self).__init__(path, executor, compresslevel)
        self.proxypass = self.makepass()

    async def write(self, content):
        loop = asyncio.get_event_loop()
        dir = os.path.dirname(self.file)
        if not os.path.isdir(dir):
            os.makedirs(dir)
        await aiowrite(self.file, content, loop, self.executor)

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
