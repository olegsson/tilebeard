from PIL import Image
import PIL.ImageOps as image_ops
from io import BytesIO

#decorator for PIL operations for applying to bytes instead of Image objects
def _apply2bytes(filter_func):
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

@_apply2bytes
def invert(img):
    return image_ops.invert(img)
