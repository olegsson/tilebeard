from PIL import Image
from io import BytesIO
import mercantile

# decorator for PIL operations for applying to bytes instead of Image objects
def apply2bytes(filter_func):
    def wrapped(bytes):
        img = Image.open(BytesIO(bytes))
        if img.mode == 'RGBA':
            *rgb, a = img.split()
            filtered_rgb = filter_func(Image.merge('RGB', (rgb)))
            filtered_img = Image.merge('RGBA', (*filtered_rgb.split(), a))
        else:
            filtered_img = filter_func(img)
        filtered_bytes = BytesIO()
        filtered_img.save(filtered_bytes, format='PNG')
        return filtered_bytes.getvalue()
    return wrapped

# decorator for initializing PIL operations that take additional arguments
# before applying them to a TileBeard instance as filters
def constructable_filter(func):

    def constructor(*args, **kwargs):

        @apply2bytes
        def wrapped(img):
            return func(img, *args, **kwargs)

    return constructor

# dict to object
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

class TileNotFound(Exception):
    pass

def num2box(z, x, y, srid='4326'):
    if srid == '4326':
        return mercantile.bounds(x, y, z)
    elif srid == '3857':
        return mercantile.xy_bounds(x, y, z)
    else:
        raise ValueError('Invalid or unsupported SRID, please use 4326 or 3857')
