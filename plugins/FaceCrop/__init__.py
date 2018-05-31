from maskgen.image_wrap import openImageFile
from maskgen.image_wrap import ImageWrapper
from maskgen.tool_set import coordsFromString
import os.path

"""
FaceCrop- Given metadata regarding face positions,
will pull relevant positional data and use that data to crop the image.
"""


def selectfacefromdata(filemap, filename, image_bounds=(0,0), cropDimensions=(1024,1024)):
    for data in filemap:
        if str(data['file_name']).__contains__(filename): #grab the right metadata
            valid_faces = [face for face in data['faces']
                          if face['face_width'] <= cropDimensions[0]/2]
            if len(valid_faces) > 0:
                #filter and sort faces
                ranked_faces = sorted(valid_faces, key=lambda k: (abs(k['face_yaw'])+abs(k['face_pitch']),
                                                                  (k['face_width'] * k['face_height'])*-1),reverse=True)
                #check for out of image bounds, return first valid.
                for face in ranked_faces:
                    center = face['chin_x'], face['right_eye_y']
                    if (center[0] + (cropDimensions[0]/2) < int(image_bounds[1]) and
                        center[1] + (cropDimensions[1]/2) < int(image_bounds[0]) and
                        center[0] - (cropDimensions[0]/2) > 0 and
                        center[1] - (cropDimensions[1]/2) > 0):
                        return face
                raise ValueError('Not enough room around any face to crop')
            else:
                raise ValueError('No Faces that match the given parameters.')


def transform(img, source, target, **kwargs):
    im_source = openImageFile(source).image_array
    dimensionX, dimensionY = coordsFromString(kwargs['crop dimensions'])
    eyePosX, eyePosY = coordsFromString(str(kwargs['right eye position'])) if 'right eye position' in kwargs else None,None
    chinPosX, chinPosY = coordsFromString(str(kwargs['chin position'])) if 'chin position' in kwargs else None,None

    filemap = kwargs['filemap'] if 'filemap' in kwargs else None
    if filemap is not None:
        face = selectfacefromdata(filemap, kwargs['donor'], im_source.shape, cropDimensions=(dimensionX,dimensionY))
        #eyePosX = face['right_eye_x']
        eyePosY = face['right_eye_y']
        chinPosX = face['chin_x']
        #chinPosY = face['chin_y']

    faceCenter = chinPosX, eyePosY

    top = (faceCenter[1] - dimensionY / 2) - (faceCenter[1] - dimensionY / 2) % 8
    left = (faceCenter[0] - dimensionX / 2) - (faceCenter[0] - dimensionX / 2) % 8

    im_source = im_source[top:top + dimensionY, left:left + dimensionX, :]

    ImageWrapper(im_source).save(target, format='PNG')
    return {"top":top, "left":left},None

def operation():
    return {'name': 'TransformCrop',
            'category': 'Transform',
            'description': 'Make a crop of the region around the center of a face.',
            'software': 'maskgen',
            'version': '.5',
            'arguments': {
                'right eye position':{
                    'type':'text',
                    'description':'Enter the pixel coordinates of the right eye as X,Y'
                },
                'chin position':{
                    'type':'text',
                    'description':'Enter the pixel coordinates of the chin as X,Y'
                },
                'crop dimensions':{
                    'type':'text',
                    'description':'Enter the pixel dimensions of the crop region as Width,Height'
                },
                'filemap':{
                    'type':'list',
                    'description':'A list of dictionaries that includes the metadata about the faces (for BatchProcess)'
                },
                'donor':{
                    'type':'file',
                    'description':'The file whose name should be looked up in the metadata (filemap)'
                }
            },
            'transitions': [
                'image.image'
            ]
            }

def suffix():
    return None