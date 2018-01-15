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
import ujson

from .tbutils import ObjDict, TileNotFound

def num2box(z, x, y, srid='4326'):
    if srid == '4326':
        return mercantile.bounds(x, y, z)
    elif srid == '3857':
        return mercantile.xy_bounds(x, y, z)
    else:
        raise ValueError('Invalid or unsupported SRID, please use 4326 or 3857')

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

def bufferize(box, buffer):
    xbuffer = (box[2] - box[0]) * buffer
    ybuffer = (box[3] - box[1]) * buffer
    return (
        box[0] - xbuffer,
        box[1] - ybuffer,
        box[2] + xbuffer,
        box[3] + ybuffer,
    )

def crop(imagefile, box):
    '''
    faster crop for uncompressed images
    '''
    with Image.open(imagefile) as image:

        world = get_world_data(imagefile, image.size)
        check_if_intersect(box, world)
        bounds = box2pix(box, world)

        if image.tile[0][0] == 'raw':

            iw, ih = image.size
            offset = image.tile[0][2]

            x = bounds[0]
            y = bounds[1]
            x1 = bounds[2]
            y1 = bounds[3]
            w = x1 - x
            h = y1 - y
            hcorr = min(h, ih-abs(y))

            image.size = (iw, hcorr)
            image.tile = [
                (
                    'raw',
                    (0, 0, iw, hcorr),
                    offset + 4 * iw * max(0, y),
                    ('RGBA', 0, 1),
                )
            ]
            return image.crop((x, min(0, y), x+w, min(h, y1)))

        return image.crop(bounds)

class ImageSource:
    '''
    Class for generating tiles on demand from image source.
    '''

    def __init__(self, imagefile, executor, srid='4326',
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
        return crop(self.file, box).resize(self.tilesize, self.resample)

    async def __call__(self, z, x, y):
        loop = asyncio.get_event_loop()
        response = BytesIO()
        box = list(num2box(z, x, y, self.srid))
        tile = await loop.run_in_executor(self.executor, self.get_tile, box)
        tile.save(response, format=self.format)
        return response.getvalue()

def get_simplify_tolerance(box, relative_tolerance):
    '''
    returns distance passed to shapely.geometry.simplify
    '''
    diagonal = math.sqrt(
        (box[2] - box[0])**2 + (box[3] - box[1])**2
    )
    return diagonal * relative_tolerance

class VectorSource:
    '''
    Class for generating tiles on demand from vector source.
    '''

    def __init__(self, vectorfile, executor,
        srid='4326', buffer=0, relative_tolerance=.0005,
        preserve_topology=True):
        self.format = 'geojson'
        self.file = vectorfile
        self.executor = executor
        self.srid = srid
        self.buffer = buffer
        self.relative_tolerance = relative_tolerance
        self.preserve_topology = preserve_topology

    async def modified(self):
        return os.path.getmtime(self.file)

    def get_tile(self, box):
        features = []
        geobox = shp.box(
            *bufferize(box, self.buffer)
        )
        tolerance = get_simplify_tolerance(box, self.relative_tolerance)
        with fiona.open(self.file, 'r') as cake:
            for feat in cake:
                cut = shp.shape(feat['geometry']).intersection(geobox)
                if cut.is_empty:
                    continue
                feat['geometry'] = shp.mapping(
                    cut.simplify(tolerance, self.preserve_topology)
                )
                features.append(feat)
        return {
            'type': 'FeatureCollection',
            'features': features,
        }

    async def __call__(self, z, x, y):
        loop = asyncio.get_event_loop()
        box = num2box(z, x, y, self.srid)
        tile = await loop.run_in_executor(self.executor, self.get_tile, box)
        return ujson.dumps(tile)
