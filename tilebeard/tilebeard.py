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
        (False, True, True): FileTile,
        (False, False, True): ProxyTile,
        (True, False, True): ProxyTile,
        (False, True, False): LazyTile,
        (True, True, False): LazyTile,
    }
    key = (not path, not url, not source)
    return types[key]

class TileBeard:
    '''
    The adapter for serving a set of tiles.
    '''

    def __init__(self, path='', url='', source='',
        template='/{}/{}/{}', frmt='png', compresslevel=0,
        max_workers=5, executor=None, session=None, minzoom=0,
        maxzoom=18, **kwargs):

        assert not (not path and not url and not source) # bleh
        self.path = path
        self.url = url
        self.template = template
        self.format = frmt
        self.template += '.' + self.format
        self.compresslevel = compresslevel
        self.session = session
        self.tile = get_tile_type(path, url, source)
        self.minzoom = minzoom
        self.maxzoom = maxzoom
        if executor is None:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
        else:
            self.executor = executor
        if source:
            if type(source) == str: # TODO: implement vector source support here
                self.source = ImageSource(source, self.executor)
                self.format = source.split('.')[-1].lower()
            else:
                self.source = source(**kwargs)
        else:
            self.source = None
            self.format = frmt
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
        path = self.path + self.template.format(*key)
        url = self.url + self.template.format(*key)

        try:
            tile = self.tile(
                path,
                self.executor,
                self.compresslevel,
                url,
                self.session,
                self.source,
                key,
            )

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
    Adapter for serving multiple layers (TileBeards).
    Meant only for on-demand tiles (and .mbtiles in the future), since
    TileBeard can already handle this on its own for premade pyramids and
    proxy urls by passing custom template arguments.
    '''

    def __init__(self, source, tilepath='', compresslevel=0,
        max_workers=5, executor=None, minzoom=0, maxzoom=18, **kwargs):

        self.minzoom = minzoom
        self.maxzoom = maxzoom
        self.source = source # formattable string or source class
        self.sourceargs = kwargs
        if tilepath:
            try:
                count = source.count('{}')
            except AttributeError:
                count = source.count

            self.tilepath = tilepath + '/{}' * count
        else:
            self.tilepath = sourcepath + '/tiles'
        self.compresslevel = compresslevel
        if executor is None:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
        else:
            self.executor = executor

    async def __call__(self, key, request_headers={}, filter=None):
        if not self.minzoom <= int(key[-3]) <= self.maxzoom:
            return NOT_FOUND
        if type(self.source) == str:
            source = self.source.format(*key[:-3])
        else:
            source = self.source
        beard = TileBeard(
            source = source,
            path = self.tilepath.format(*key[:-3]),
            compresslevel = self.compresslevel,
            executor = self.executor, # joint executor for all childbeards
            minzoom = self.minzoom,
            maxzoom = self.maxzoom,
            **self.sourceargs
        )
        return await beard(
            key[-3:],
            request_headers=request_headers,
            filter=filter
        )
