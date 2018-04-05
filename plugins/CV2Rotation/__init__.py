import cv2
from maskgen.image_wrap import ImageWrapper
from maskgen.tool_set import resizeImage,rotateImage,serializeMatrix

def transform(img,source,target,**kwargs):
    rotation = int(kwargs['rotation'])
    imgdata = img.to_array()
    #if len(imgdata.shape) > 2:
    #    imgdata = cv2.cvtColor(imgdata, cv2.COLOR_RGB2GRAY)
    rows, cols, channels = imgdata.shape
    M = cv2.getRotationMatrix2D((cols / 2, rows / 2), rotation, 1)
    constant = int(imgdata.max())
    rotated_img = cv2.warpAffine(imgdata, M, (cols, rows), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    #rotated_img = rotateImage(rotation,(rows / 2,cols / 2),imgdata)
        #out_img = cv2.cvtColor(rotated_img, cv2.COLOR_GRAY2RGB)
        # display(out_img, 'rotation')
    ImageWrapper(rotated_img).save(target)
    return {'transform matrix': serializeMatrix(
        M)}, None

# the actual link name to be used.
# the category to be shown
def operation():
  return {
          'category': 'Transform',
          'name': 'TransformRotate',
          'description':'Rotate an entire image without changing dimensions',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments': {
              'rotation': {
                'type': 'int[-270:270]',
                'defaultValue':None,
                'description': 'Rotation angle counter-clockwise'
              },
              'local': {
                  'type': 'text',
                  'defaultvalue': 'no'
              }
          },
          'transitions': [
              'image.image'
          ]
          }
