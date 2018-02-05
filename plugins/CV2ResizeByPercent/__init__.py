import cv2
from maskgen.image_wrap import ImageWrapper
from maskgen.tool_set import resizeImage


def transform(img, source, target, **kwargs):
    cv_image =img.to_array()
    shape = cv_image.shape
    percentageWidth = float(kwargs['percentage_width'])
    percentageHeight = float(kwargs['percentage_height'])
    pixelWidth = int(shape[1] * percentageWidth)
    pixelHeight = int(shape[0] * percentageHeight)
    pixelWidth = pixelWidth - pixelWidth % 8
    pixelHeight = pixelHeight - pixelHeight % 8
    ImageWrapper(resizeImage(cv_image, (pixelHeight,pixelWidth), kwargs['interpolation'])).save(target)
    return None, None


# the actual link name to be used.
# the category to be shown
def operation():
    return {
        'category': 'Transform',
        'name': 'TransformResize',
        'description': 'Resize an entire image dimensions',
        'software': 'OpenCV',
        'version': cv2.__version__,
        'arguments': {
            'percentage_width':
                {'type': "float[0:0.99]", 'description': 'the percentage of pixels to retained horizontal'},
            'percentage_height':
                {'type': "float[0:0.99]", 'description': 'the percentage of pixels to retained vertically'},
            'interpolation': {
                "type": "list",
                "defaultValue": "image",
                "values": [
                    "bilinear",
                    "bicubic",
                    "cubic",
                    "mesh",
                    "lanczos",
                    "nearest"
                ],
                "description": "Interpolation is used to resize entire composite images. "
            }
        },
        'transitions': [
            'image.image'
        ]
    }
