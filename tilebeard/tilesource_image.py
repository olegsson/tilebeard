import math
from PIL import Image
import asyncio
from io import BytesIO
import os

from .tbutils import ObjDict, TileNotFound, num2box

def box2pix(box, world):
    '''
    bounding box to pixel bounds of source image
    '''
    left = (box[0] - world.W) / world.xres
    upper = (world.N - box[3]) / world.yres
    right = left + (box[2] - box[0]) / world.xres
    lower = upper + (box[3] - box[1]) / world.yres
    return tuple(
        round(x) for x in (left, upper, right, lower)
    )

def get_world_data(imagefile, imagesize):
    # TODO: implement support for skewed images...
    worldfile = imagefile[:-2]+imagefile[-1]+'w'
    with open(worldfile, 'r') as f:
        data = [float(x) for x in f.read().split('\n')]
    xres = data[0]
    yres = -data[3]
    w = xres * imagesize[0]
    h = yres * imagesize[1]
    xw = data[4]
    yn = data[5]
    xe = xw + w
    ys = yn - h
    return ObjDict({
        'xres': xres,
        'yres': yres,
        # 'width': w,
        # 'height': h,
        'N': yn,
        'E': xe,
        'S': ys,
        'W': xw,
        # 'box': (xe, ys, xw, yn),
    })

def check_if_intersect(box, world):
    if box[0] > world.E or box[1] > world.N or box[2] < world.W or box[3] < world.S:
        raise TileNotFound

class ImageSource:
    '''
    Class for generating tiles on demand from image source.
    '''

    def __init__(self, imagefile, executor, srid='3857',
        frmt='PNG', tilesize=(256, 256), resample=Image.BILINEAR):
        self.tilesize = tilesize
        self.resample = resample
        self.file = imagefile
        self.executor = executor
        self.format = frmt
        self.srid = srid

    async def modified(self):
        return os.path.getmtime(self.file)

    def get_tile(self, box):
        with Image.open(self.file) as image:
            world = get_world_data(self.file, image.size)
            check_if_intersect(box, world)
            bounds = box2pix(box, world)
            return image.crop(bounds).resize(self.tilesize, self.resample)

    async def __call__(self, z, x, y):
        loop = asyncio.get_event_loop()
        response = BytesIO()
        box = list(num2box(z, x, y, self.srid))
        tile = await loop.run_in_executor(self.executor, self.get_tile, box)
        tile.save(response, format=self.format)
        return response.getvalue()
