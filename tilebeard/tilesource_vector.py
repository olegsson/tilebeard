import math
from PIL import Image
import asyncio
from io import BytesIO
import os
import mercantile
import fiona
import shapely

from .tbutils import ObjDict, TileNotFound, num2box

class VectorSource:
    '''
    Class for generating tiles on demand from vector source.
    '''

    def __init__(self, vectorfile, executor):
        self.file = vectorfile
        self.executor = executor

    async def modified(self):
        return os.path.getmtime(self.file)

    def get_tile(self, box):
        features = []
        with fiona.open(self.file, 'r') as src:
            pass

    async def __call__(self, z, x, y):
        loop = asyncio.get_event_loop()
        box = shapely.box(*num2box(z, x, y))
