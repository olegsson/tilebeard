# tilebeard

Attempt at a minimal WMTS adapter for python 3.5+ async networking frameworks, for use with tiles pre-rendered with tools like [gdal2tiles.py](http://www.gdal.org/gdal2tiles.html), or as a proxy to an existing WMTS with optional local caching. Hosted here for convenience and potentially some feedback. This package is a work in progress an experiment at several things, proceed at own risk.

Largely inspired by [TileStache](https://github.com/TileStache/TileStache)

## installation

`git clone` and `python setup.py install`

#### requirements

Python 3.5+

aiohttp (for async requests in proxy mode)

## usage

```
from tilebeard import TileBeard

tiles = TileBeard(path='/path/to/tiles')
```
or
```
tiles = TileBeard(url='some.wmts.url')
```
or
```
tiles = TileBeard(
  url='some.wmts.url',
  path='/path/to/cache/tiles/to'
)
```

### getting tiles
```
status_code, headers, content = await tiles(key, [request_headers])
```
`key` can be tuple of parameters (eg. z, x, y) or path, conforming to template format (see below)
if `request_headers` are passed to the call, tilebeard returns `304 Not Modified` response when appropriate

### additional `__init__` arguments
`template` (defaults to `'/{}/{}/{}.png'`) indicates call format, used to build dictionary of tiles

`max_workers` (defaults to `2`) passed to `concurrent.futures.ThreadPoolExecutor` for async file read

`compresslevel` (defaults to `0`) passed to gzip for response compression if needed

## license

[MIT](https://opensource.org/licenses/MIT)

## future

* should make this more of a WMTS library (as it currently stands it's compatible with mostly any dir tree)
* proper excepion handling
* .mbtiles support
* possibly PostGIS support
* examples with various networking frameworks
* other stuff
