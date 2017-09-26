import numpy
from maskgen import tool_set
from maskgen import image_wrap


def widthandheight(img):
    a = numpy.where(img != 0)
    bbox = numpy.min(a[0]), numpy.max(a[0]), numpy.min(a[1]), numpy.max(a[1])
    h, w = bbox[1] - bbox[0], bbox[3] - bbox[2]
    return bbox[2], bbox[0], w, h


def transform(img, source, target, **kwargs):
    mask = numpy.asarray(tool_set.openImageFile(kwargs['inputmaskname']).to_mask())
    source_im = numpy.asarray(tool_set.openImageFile(source))
    paste_x = int(kwargs['paste_x'])
    paste_y = int(kwargs['paste_y'])
    x, y, w, h = widthandheight(mask)
    w += w % 2
    h += h % 2
    image_to_cover = numpy.copy(source_im)
    flipped_mask = 255 - mask
    for c in range(0, source_im.shape[2]):
        image_to_cover[paste_y:paste_y + h, paste_x:paste_x + w, c] = \
            image_to_cover[paste_y:paste_y + h, paste_x:paste_x + w, c] * \
            (flipped_mask[y:y + h, x:x + w] / 255) + \
            image_to_cover[y:y + h, x:x + w, c] * \
            (mask[y:y + h, x:x + w] / 255)
    target_im = image_wrap.ImageWrapper(image_to_cover)
    target_im.save(target)
    return {'purpose': 'clone'}, None


def operation():
    return {
        'category': "Paste",
        'name': "PasteSampled",
        'description': 'Local Clone the pixels as indicated in the provided input mask to the location indicated',
        'software': 'OpenCV',
        'version': '2.4.13',
        'arguments': {
            "purpose": {
                "type": "list",
                "values": ["clone"],
                "description": "clone test."
            },
            'inputmaskname': {
                'type': 'imagefile',
                'defaultvalue': None,
                'description': 'Mask image where black pixels identify region to blur'
            },
            'paste_x': {
                'type': 'int[0:10000000]',
                'defaultvalue': None,
                'description': 'Upper left corner of the bounding rectangle indicated the column to paste the cloned image'
            },
            'paste_y': {
                'type': 'int[0:10000000]',
                'defaultvalue': None,
                'description': 'Upper left corner of the bounding rectangle indicated the row to paste the cloned image'
            }
        },
        'transitions': [
            'image.image'
        ]
    }
