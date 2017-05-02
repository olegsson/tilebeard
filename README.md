# tilebeard

Attempt at a minimal WMTS adapter for existing python networking frameworks, with tiles pre-rendered with tools like [gdal2tiles.py](http://www.gdal.org/gdal2tiles.html), or as a proxy to an existing WMTS with optional local caching. Hosted here for convenience and potentially some feedback. Done as an experiment at several things, proceed at own risk.

Largely inspired by [TileStache](https://github.com/TileStache/TileStache)

## installation

`git clone` and `python setup.py install`

## usage

```
from tilebeard import TileBeard

tb = TileBeard(path='/path/to/tiles')
```
or
```
tb = TileBeard(url='some.wmts.url')
```
or
```
tb = TileBeard(
  url='some.wmts.url',
  path='/path/to/cache/tiles/to'
)
```

### getting tiles
```
headers, content = tb(arg)
```
`arg` can be tuple of parameters or path, conforming to template format (look below)

### or in Python 3.5+
```
from tilebeard import AIOBeard

tb = AIOBeard(*args, **kwargs)
```
The `AIOBeard` class works the same as `TileBeard` except it's `__call__` method is a coroutine to be used with event loop of choice, as in:
```
  headers, content = await tb(arg)
```

### additional `__init__` arguments
`template` (defaults to `'/{}/{}/{}.png'`) indicates call format, used to build dictionary of tiles

`compresslevel` (defaults to `0`) passed to gzip for response compression if needed

## license

[MIT](https://opensource.org/licenses/MIT)

## future

* should make this more of a WMTS library (as it currently stands it's compatible with mostly any dir tree)
* proper excepion handling
* possibly PostGIS compatibility
* examples with various networking frameworks
* other stuff
