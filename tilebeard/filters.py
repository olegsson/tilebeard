from PIL import Image
import PIL.ImageOps as image_ops
from io import BytesIO

def _apply2bytes(filter_func):
    def _wrapped(bytes):
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
    return _wrapped

@_apply2bytes
def invert(img):
    return image_ops.invert(img)

file = '/code/gekom/bora2/web/geotmp/tiles/201705111800/CLFLO/10/545/636.png'

with open(file, 'rb') as f:
    b = f.read()
