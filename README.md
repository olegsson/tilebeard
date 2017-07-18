# tilebeard

Attempt at a minimal adapter for serving map tiles with existing python 3.5+ async networking frameworks, for use with tiles pre-rendered with tools like [gdal2tiles.py](http://www.gdal.org/gdal2tiles.html), as a proxy to an existing tile service with optional local caching, or for dynamically generating tiles from a georeferenced image or a custom source. Hosted here for convenience and potentially some feedback. This package is a work in progress and an experiment at several things, proceed at own risk.

Largely inspired by [TileStache](https://github.com/TileStache/TileStache)

## installation

Install requirements, then:
`git clone` and `python setup.py install` or `pip install tilebeard`

#### requirements

Python 3.5+

aiohttp (for async requests in proxy mode)

Pillow (for dynamic tile generation from a source image and applying filters to output on-demand)

fiona, shapely (for parsing vector files)

ujson (for geojson vectortile output)

mercantile (for CRS operations)

## usage

### initializing a tile serving object

#### TileBeard

```
tiles = TileBeard(path='', url='', source='',
        template='/{}/{}/{}', frmt='png', compresslevel=0,
        max_workers=5, executor=None, session=None, minzoom=0,
        maxzoom=18, **source_kwargs)
```

for serving premade tiles:
```
from tilebeard import TileBeard

tiles = TileBeard(path='/path/to/tiles')
```

for serving tiles as proxy:
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

for generating tiles on demand from source image or custom source object:
```
tiles = TileBeard(
    path='/path/to/cache/tiles/to',
    source='/path/to/source/image.tif'
)
```
TileBeard's builtin source classes currently support GeoJSON and shapefiles, as well as any and all image formats that Pillow supports.

#### ClusterBeard

```
tiles = ClusterBeard(source, frmt='png', tilepath='', compresslevel=0,
    max_workers=5, executor=None, minzoom=0, maxzoom=18, **source_kwargs)
```

The ClusterBeard class is meant for serving multiple layers of dynamically generated tiles.
Its `source` argument can either be a formattable string (to be evaluated on call) or a custom tilesource class.

### getting tiles
```
status_code, headers, content = await tiles(key, request_headers={}, filter=None)
```
`key` should be a tuple of parameters (eg. `(z, x, y)` or `(layer, z, x, y)`), conforming to template format.
In ClusterBeard's case, all members of `key` other than the last three (x, y, z) are used to format the source string or are passed to a custom source class' constructor.

If `request_headers` (dict) is passed to the call, tilebeard returns `304 Not Modified` response when appropriate.

#### filters
TileBeard supports filters for on-demand modification of tiles.
The package currently only contains wrappers around some `PIL.ImageOps` methods (mostly all that preserve image resolution) but theoretically any function that takes a bytestring (or utf8 string for text formats like GeoJSON) can be implemented as a filter.

```
from tilebeard.filters import raster_ops

status_code, headers, content = await tiles(key, filter=raster_ops.invert)
```
or in case of `PIL.ImageOps` methods that take additional arguments:
```
filter = raster_ops.posterize(bits=4)
status_code, headers, content = await tiles(key, filter=filter)
```

## license

[MIT](https://opensource.org/licenses/MIT)

## future

* proper exception handling
* .mbtiles support
* possibly PostGIS support
* examples with various networking frameworks
* other stuff
