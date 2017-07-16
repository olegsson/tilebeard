import math
from PIL import Image
import asyncio
from io import BytesIO
import os
import mercantile
import fiona
from shapely import speedups
if speedups.available:
    speedups.enable()
from shapely import geometry as shp

from .tbutils import ObjDict, TileNotFound, num2box

class VectorSource:
    '''
    Class for generating tiles on demand from vector source.
    '''

    def __init__(self, vectorfile, executor, srid='4326'):
        self.file = vectorfile
        self.executor = executor
        self.srid = srid

    async def modified(self):
        return os.path.getmtime(self.file)

    def get_tile(self, box):
        features = []
        with fiona.open(self.file, 'r') as src:
            for feat in src:
                cut = shp.shape(feat).geometry.intersection(box)
                if cut.is_empty:
                    continue
                feat['geometry'] = shp.mapping(cut)
                features.append(feat)
        return {
            'type': 'FeatureCollection',
            'features': features,
        }

    async def __call__(self, z, x, y):
        loop = asyncio.get_event_loop()
        box = shp.box(*num2box(z, x, y, self.srid))
        tile = await loop.run_in_executor(self.executor, self.get_tile, box)
        return tile
