import cv2
from maskgen.image_wrap import ImageWrapper
from maskgen.tool_set import resizeImage

def transform(img,source,target,**kwargs):
    pixelWidth = int(kwargs['width'])
    pixelHeight = int(kwargs['height'])
    ImageWrapper(resizeImage(img.to_array(),(pixelHeight,pixelWidth),kwargs['interpolation'])).save(target)
    return None, None

# the actual link name to be used.
# the category to be shown
def operation():
  return {
          'category': 'Transform',
          'name': 'TransformResize',
          'description':'Resize an entire image dimensions',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments': {
              'width': {
                'type': 'int[1:10000000]',
                'defaultValue':None,
                'description': 'New width size'
              },
              'height': {
                  'type': 'int[1:10000000]',
                  'defaultValue':None,
                  'description': 'New idmage height'
              },
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
