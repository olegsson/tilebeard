import os
import gzip
import re
from glob import iglob
from collections import OrderedDict
import asyncio
from aiohttp import ClientSession
from concurrent.futures import ThreadPoolExecutor

MIMETYPES = OrderedDict({
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'json': 'application/json',
    'tif': 'image/tiff',
    '': 'text/plain',
})

BLANK = (
    {'Content-Type': 'application/octet-stream'},
    b'',
)

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

class Tile:
    '''
    Callable class for handling individual tiles.
    Stores filepath and headers, returns them on __call__.
    '''

    def __init__(self, path, loop, executor, compresslevel=0):
        self.ext = path.split('.')[-1].lower()
        self.file = path
        self.executor = executor
        self.loop = loop # asyncio.get_event_loop()
        for ext in MIMETYPES.keys():
            try:
                if ext in self.ext:
                    self.headers = {
                        'Content-Type': MIMETYPES[ext]
                    }
                    break
            except TypeError:
                pass

        self.respond = self.makerespond(compresslevel)

    async def read(self):
        return await aioread(self.file, self.loop, self.executor)

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
                return self.headers, content
        else:
            def respond(content):
                return self.headers, content

        return respond

    async def __call__(self):
        content = await self.read()
        return self.respond(content)

class ProxyTile(Tile):
    '''
    Extends Tile class to handle remote tile urls and cache content locally.
    '''

    def __init__(self, url, session, loop, executor, path=None, compresslevel=0):
        super(ProxyTile, self).__init__(path, loop, executor, compresslevel)
        self.url = url
        self.session = session
        self.executor = executor
        self.loop = asyncio.get_event_loop()
        self.proxypass = self.makepass()

    async def write(self, content):
        await aiowrite(self.file, content, self.loop, self.executor)

    def makepass(self):
        if self.file is None:
            async def proxypass():
                async with self.session.get(self.url) as response:
                    return await response.read()
        else:
            async def proxypass():
                try:
                    content = await self.read()
                    return content
                except FileNotFoundError:
                    async with self.session.get(self.url) as response:
                        content = await response.read()
                    dir = os.path.dirname(self.file)
                    if not os.path.isdir(dir):
                        os.makedirs(dir)
                    await self.write(content)
                    return content
        return proxypass

    async def __call__(self):
        content = await self.proxypass()
        return self.respond(content)

class TileBeard:
    '''
    The adapter for serving a set of tiles. Is bound to dir and/or url.
    '''

    __beard = {}

    def __init__(self, path=None, url=None, template='/{}/{}/{}.png', max_workers=10, compresslevel=0):
        self.path = path
        self.url = url
        self.template = template
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.compresslevel = compresslevel
        self.loop = asyncio.get_event_loop()
        if url is None:
            if path is not None:
                stars = '*' * template.count('{}')
                for file in iglob(path+template.format(*stars)):
                    self.__beard[re.sub(path, '', file)] = Tile(file, self.loop, self.executor, self.compresslevel)
        else:
            self.session = ClientSession()

    async def __call__(self, key):
        if type(key) in (tuple, list):
            key = self.template.format(*key)
        if key in self.__beard:
            return await self.__beard[key]()
        else:
            if self.url is None:
                return BLANK
            else:
                path = None
                if self.path is not None:
                    path = self.path + key
                url = self.url + key
                tile = ProxyTile(url, self.session, self.loop, self.executor, path, self.compresslevel)
                self.__beard[key] = tile
                return await tile()
