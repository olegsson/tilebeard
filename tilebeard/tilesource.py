# from osgeo import gdal
# from shapely.geometry import box
# from scipy import misc
from sys import getsizeof
import math
from PIL import Image

class ObjDict(dict):

    def __init__(self, *args, **kwargs):
        super(ObjDict, self).__init__(*args, **kwargs)
        self.__dict__.update(*args, **kwargs)

    def __setitem__(self, key, value):
        super(ObjDict, self).__setitem__(key, value)
        self.__dict__[key] = value

    def update(self, other=None, **kwargs):
        super(ObjDict, self).update(other, **kwargs)
        if other is not None:
            self.__dict__.update(other)
        if kwargs != {}:
            self.__dict__.update(kwargs)

def num2deg(xtile, ytile, zoom):
    '''
    osm xyz tilename to coordinates
    from http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Python
    '''
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lon_deg, lat_deg)

def num2box(xtile, ytile, zoom):
    '''
    tilename to bounding rectangle
    '''
    xe, yn = num2deg(xtile, ytile, zoom)
    xw, ys = num2deg(xtile+1, ytile+1, zoom)
    return (xe, ys, xw, yn)

def box2pix(box, world):
    '''
    lonlat bounding box to pixel bounds of source image
    '''
    left = math.floor(
        (box[0] - world.E) / world.xres
    )
    upper = math.floor(
        (world.N - box[3]) / world.yres
    )
    right = left + math.ceil(
        (box[2] - box[0]) / world.xres
    )
    lower = upper + math.ceil(
        (box[3] - box[1]) / world.yres
    )
    return (left, upper, right, lower)

def get_world_data(imagefile, imagesize):
    worldfile = imagefile[:-2]+imagefile[-1]+'w'
    with open(worldfile, 'r') as f:
        data = [float(x) for x in f.read().split('\n')]
    xres = data[0]
    yres = -data[3]
    w = xres * imagesize[0]
    h = yres * imagesize[1]
    xe = data[4]
    yn = data[5]
    xw = xe + w
    ys = yn - h
    return ObjDict({
        'xres': xres,
        'yres': yres,
        'width': w,
        'height': h,
        'N': yn,
        'E': xe,
        'S': ys,
        'W': xw,
        'box': (xe, ys, xw, yn),
    })

class TileSource:

    def __init__(self, imagefile, tilesize=(256, 256), resample=Image.BILINEAR):
        self.tilesize = tilesize
        self.resample = resample
        self.image = Image.open(imagefile)
        self.world = get_world_data(imagefile, self.image.size)

    def get_tile(self, x, y, z):
        box = num2box(x, y, z)
        bounds = box2pix(
            box,
            self.world
        )
        return self.image.crop(bounds).resize(self.tilesize, self.resample)
#%%

# file = '/code/contrib/tilebeard/testing/T2.png'
# outfile = '/code/contrib/tilebeard/testing/test.png'
#
# img = TileSource(file)
# %timeit tile = img.get_tile(140, 90, 8)
