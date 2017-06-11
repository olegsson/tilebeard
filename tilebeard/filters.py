from PIL import ImageOps

from tbutils import apply2bytes, constructable_filter, ObjDict

# wrapper around some of PIL's ImageOps methods

image_ops = {
    imgop: apply2bytes(
        ImageOps.__dict__[imgop]
    ) for imgop in (
        'invert',
        'grayscale',
    )
}

image_ops.update({
    imgop: constructable_filter(
        ImageOps.__dict__[imgop]
    ) for imgop in (
        'autocontrast',
        'colorize',
        'equalize',
        'posterize',
        'solarize',
    )
})

image_ops = ObjDict(image_ops)
