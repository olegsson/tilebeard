import re
from glob import iglob
import asyncio
from aiohttp import ClientSession
from concurrent.futures import ThreadPoolExecutor
from .tile import FileTile, ProxyTile, LazyTile
from .tilesource import ImageSource

# NOTE: removing this, filters should be passed as functions for pluggability
# from .filters import *
# _filters = {
#     'invert': invert
# }

NOT_FOUND = (
    404,
    {'Content-Type': 'text/plain'},
    b'not found',
)

NOT_MODIFIED = (
    304,
    {'Content-Type': 'text/plain'},
    b'not modified',
)

def get_tile_type(path, url, source): # graceful as a drunk bear...
    types = {
        (False, True, True): Tile,
        (False, False, True): ProxyTile,
        (True, False, True): ProxyTile,
        (False, True, False): LazyTile,
        (True, True, False): LazyTile,
    }
    key = (not path, not url, not source)
    return types[key]

class TileBeard:
    '''
    The adapter for serving a set of tiles. Is bound to dir and/or url.
    '''

    def __init__(self, path='', url='', sourcefile='', template='/{}/{}/{}', frmt='png', max_workers=2, compresslevel=0):
        # assert not (path is None and url is None and source is None)
        self.path = path
        self.url = url
        self.template = template
        if frmt:
            self.template += '.' + frmt
        self.format = frmt
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.source = None
        if sourcefile:
            self.source = ImageSource(source, self.executor)
        self.compresslevel = compresslevel
        self.session = None
        self.tile = get_tile_type(path, url, sourcefile)
        if path is not None:
            stars = '*' * template.count('{}')
            globstring = path + template.format(*stars)
            def count(self):
                c = 0
                for file in iglob(globstring):
                    c += 1
                return c

    async def __call__(self, key, request_headers={}, filter=None):
        if self.session is None and self.url is not None:
            self.session = ClientSession()
        if type(key) in (tuple, list):
            async def sourcecall():
                return await self.source(key)
            key = self.template.format(*key)
        elif self.tile is LazyTile:
            raise ValueError('LazyTile call requires tuple (z, x, y)')

        try:
            with self.tile(
                self.path+key,
                self.executor,
                self.compresslevel,
                self.url+key,
                self.session,
                self.source,
                key,
            ) as tile:

                check_headers = [
                    key for key in ('If-Modified-Since', 'If-None-Match') if key in request_headers
                ]

                if check_headers != []:
                    checkvals = tile.modified() # NOTE: make this support ProxyTile
                    checks = [
                        request_headers[key] == checkvals[i] for i, key in enumerate(check_headers)
                    ]
                    if sum(checks) == len(checks):
                        return NOT_MODIFIED

                response = await tile()

                if filter is not None:
                    response = (*response[:2], filter(response[-1]))

                return response

        except FileNotFoundError:
            return NOT_FOUND

class ClusterBeard:
    '''
    Adapter for serving multiple layers (TileBeards) piled up in a single
    directory (meant only for on-demand tiles and .mbtiles in the future, since TileBeard can already handle this on its own for premade pyramids and urls)
    '''

    def __init__(self):
        pass
