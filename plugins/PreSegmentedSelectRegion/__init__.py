from maskgen.segmentation.segmanage import select_region, convert_color, find_segmentation_classifier, \
    segmentation_classification
import cv2

"""
Selected a region using a presegmented image descriptor.
A directory contains PNG images, each with the same name (different suffix) as the source image (md5 name).
Each PNG contains pixels with colors associated their assigned classification, as determined another algorithm.
A classifications.csv file in the same directory contains the mapping of color to classification.
Example contents:
"[200,100,200]",house

Pick one color of all colors in the image, create a mask with the pixels associated with the chosen color set to white.
Save the mask as the target image.  The result of the transform includes a variable 'subject' set to the classification of the chosen color.
"""


def transform(img, source, target, **kwargs):
    segmentation_directory = kwargs['segmentation_directory']
    segmentation_color = kwargs['color'] if 'color' in kwargs else None
    source = kwargs['alternate_source'] if 'alternate_source' in kwargs else source
    segmentation_color = convert_color(segmentation_color)
    segment_mask = find_segmentation_classifier(source, segmentation_directory)
    if segment_mask is None:
        return None, 'Cannot find segmentation mask'
    newimg, segmentation_color = select_region(img, segment_mask, segmentation_color)
    newimg.save(target)
    return {'subject': segmentation_classification(segmentation_directory, segmentation_color)}, None


# the actual link name to be used.
# the category to be shown
def operation():
    return {'name': 'SelectRegion',
            'category': 'Select',
            'description': 'Use a set of presegmented images to pick a select region and purpose. ',
            'software': 'OpenCV',
            'version': cv2.__version__,
            'arguments':
                {
                    'segmentation_directory': {
                        'type': 'imagefile',
                        'defaultvalue': None,
                        'description': 'Directory containing the image segments'
                    },
                    'color': {
                        'type': 'string',
                        'defaultvalue': None,
                        'description': 'The color to be used for classification (e.g. [100,200,130])'
                    }
                },
            'output':
                {
                    'subject': {
                        'type': 'string',
                        'description': 'the subject name of the chosen segment of an image'
                    }
                },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return None
