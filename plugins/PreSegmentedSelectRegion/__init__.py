from maskgen.segmentation.segmanage import select_region, convert_color,find_segmentation_classifier,segmentation_classification
"""
Use a presegmented image descriptor
"""

def transform(img,source,target,**kwargs):
    segmentation_directory = kwargs['segmentation_directory']
    segmentation_color = kwargs['color'] if 'color' in kwargs else None
    segmentation_color = convert_color(segmentation_color)
    segment_mask = find_segmentation_classifier(source, segmentation_directory)
    if segment_mask is None:
        return None, 'Cannot find segmentation mask'
    newimg, segmentation_color = select_region(img,segment_mask,segmentation_color)
    newimg.save(target)
    return {'purpose' : segmentation_classification(segmentation_directory,segmentation_color)}, None

# the actual link name to be used. 
# the category to be shown
def operation():
  return {'name':'SelectRegion',
          'category':'Select',
          'description':'Use a set of presegmented images to pick a select region and purpose ',
          'software':'OpenCV',
          'version':'2.4.13',
          'arguments':
              {'segmentation_directory':{
                  'type':'imagefile',
                  'defaultvalue':None,
                  'description':'Directory containing the image segments'
              },
              'color': {
                      'type': 'string',
                      'defaultvalue': None,
                      'description': 'The color to be used for classification (e.g. [100,200,130])'
                  }
          },
          'transitions': [
              'image.image'
              ]
          }

def suffix():
    return None

