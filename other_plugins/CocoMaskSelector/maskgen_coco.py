from pycocotools.coco import COCO
import numpy as np
import logging
import os
import sys
import cv2
import shutil
import json

"""
COCO SUPPORT
"""

def _mapSubject(annotation,mapping):
    """
    map annotation category_id to a subject
    :param mapping:
    :param annotation:
    :return:
    @type mapping: dict
    """
    return mapping[annotation['category_id']] if annotation['category_id']  in mapping else 'man-made object'

def createMaskImage(image_array, imagefilename, coco, lookup, subjectMapping={}, areaConstraint=(0,sys.maxint)):
    """
    Given an image and its Coco data, pick a mask from the segmented image.
    :param image
    :param imageData:
    :return:
    @type imageData: dict
    @type image_array: numpy.array
    @type coco: COCO
    @type lookup: dict
    """
    def defaultMask(image):
        h, w = image.size
        real_mask = np.zeros((w, h), dtype=np.uint8)
        real_mask[w / 4:3 * w / 4, h / 4:3 * h / 4] = 255
        return 'other',real_mask
    imgId = lookup[os.path.split(imagefilename)[1]]
    imageData = coco.loadImgs(ids=[imgId])[0]
    annIds = coco.getAnnIds(imgIds=[imgId])
    annotations = coco.loadAnns(annIds)
    logging.getLogger('maskgen').info('Processing image name: {}'.format(imagefilename))
    image_width,image_height = image_array.shape[0],image_array.shape[1]
    factor = float(imageData['width']) / image_width
    valid_annotations = [annotation for annotation in annotations
        if annotation['area'] * factor >= areaConstraint[0] and annotation['area'] * factor <= areaConstraint[1]]
    if len(valid_annotations) > 0:
        position = np.random.randint(0, len(valid_annotations))
        annotation = annotations[position]
        real_mask = coco.annToMask(annotation)
        real_mask = real_mask.astype(np.uint8)
        real_mask[real_mask>0] = 255
        if real_mask.shape != (image_width, image_height):
            real_mask = cv2.resize(real_mask,(image_height,image_width))
        subject = _mapSubject(annotation,subjectMapping)
        return subject,real_mask
    return defaultMask(image)

        # mask[real_mask > 0]  = [color/65536,color%65536/256,color%256]


def loadCoco(annotationsFile):
    return COCO(annotationsFile)

def createFileNameToIDLookup(coco,imgIds=[], catIds=[]):
    """
    Create an index of file name to coco image ID
    :param coco:
    :return:
    @type coco: COCO
    """
    return { image_data['file_name']:image_data['id'] for image_data in coco.loadImgs(coco.getImgIds(imgIds=imgIds,catIds=catIds))}

def createMaskImageWithParams(image_array, imagefilename, params, areaConstraint=(0,sys.maxint)):
    """
    Using parameters for the coco and coco.index as they would appear in the global state,
    create mask using one of the select annotations.
    @see createBatchProjectGlobalState.
    :param image_array:
    :param imagefilename:
    :param params:
    :param areaConstraint:
    :return:
    @type image_array: numpy.ndarray
    @type params: dict
    """
    if 'coco.annotations'  in params:
        annotationPath = params['coco.annotations']
        if not os.path.exits(annotationPath):
            logging.getLogger('maskgen').error(
                'Cannot load COCO annotations.  Annotation path set to coco.annotations is invalid.')
            return None,None
            coco = COCO(annotationPath)
    else:
        if 'coco' not in params:
            logging.getLogger('maskgen').error('Cannot build mask.  Missing parameter coco.')
            return None,None
        coco = params['coco']
    index = params['coco.index'] if 'coco.index' in params else createFileNameToIDLookup(coco)
    return createMaskImage(image_array, imagefilename, coco,index,areaConstraint=areaConstraint)

def createBatchProjectGlobalState(global_state):
    """
    Check the global state for a batch project.  Initialize coco and return additions to the global state if missing
    :param global_state:
    :return:
    @type global_state: dict
    """
    if 'coco.annotations' not in global_state:
        logging.getLogger('maskgen').error('Cannot load COCO annotations.  Missing parameter coco.annotations.')
        return {}
    annotationPath = global_state['coco.annotations']
    if not os.path.exists(annotationPath):
        logging.getLogger('maskgen').error('Cannot load COCO annotations.  Annotation path set to coco.annotations is invalid.')
        return {}
    coco = loadCoco(annotationPath)
    return {'coco' : coco, 'coco.index' : createFileNameToIDLookup(coco), 'coco.subject': {}}


def moveValidImages(image_dir,target_dir,annotationPath,areaConstraint=(0,sys.maxint),maxCount=None, newAnnotationPath=None):
    """
        Move the images from the source folder to the target folder if they represent a valid
        image that contains images that meet the area constraints.
        Download the image from flickr if missing.
        If image_dir and target_dir are the same,  images  that do not meet the criteria are removed.
    :param image_dir:
    :param target_dir:
    :param annotationPath:
    :param areaConstraint:
    :param maxCount: maximum number of images to move/download
    :param newAnnotationPath: if provided, save the annotations for the select images
    :return:
    """
    coco = COCO(annotationPath)
    keep = []
    annotations_to_keep = []
    for imgId in coco.getImgIds():
        if maxCount is not None and len(keep) >= maxCount:
            break
        if imgId not in coco.anns:
            continue
        #this download is broken...downloading invalid 500x500 images!
        coco.download(tarDir=image_dir, imgIds=[imgId])
        imageData = coco.loadImgs(ids=[imgId])[0]
        target_file = os.path.join(target_dir,imageData['file_name'])
        source_file = os.path.join(image_dir, imageData['file_name'])
        if not os.path.exists(target_file):
            logging.getLogger('maskgen').warn('File Not Found: {}'.format(imageData['file_name']))
        else:
            annotations = coco.loadAnns(ids=[imgId])
            valid_annotations = [annotation for annotation in annotations
                if annotation['area'] >= areaConstraint[0] and annotation['area'] <= areaConstraint[1]]
            if len(valid_annotations) > 0:
                if source_file != target_file:
                    shutil.move(source_file,target_file)
                keep.append(imgId)
                annotations_to_keep.extend(valid_annotations)
            elif source_file == target_file:
                os.remove(source_file)
    if newAnnotationPath is not None:
        dataset = {'info': coco.dataset['info'],
                   'images': coco.loadImgs(ids=keep),
                   'categories': coco.dataset['categories'],
                   'annotations': annotations_to_keep}
        with open(newAnnotationPath, 'w') as f:
            json.dump(dataset, f, indent=2, encoding='utf-8')

def createSubset(annotationPath,filename, areaConstraint=(0,sys.maxint),maxCount=None):
    """
        Move the images from the source folder to the target folder if they represent a valid
        image that contains images that meet the area constraints.
        Download the image from flickr if missing.
        If image_dir and target_dir are the same,  images  that do not meet the criteria are removed.
    :param image_dir:
    :param target_dir:
    :param annotationPath:
    :param areaConstraint:
    :param maxCount: maximum number of images to move/download
    :return:
    """
    coco = COCO(annotationPath)
    keep = []
    annotations_to_keep = []
    for imgId in coco.getImgIds():
        if maxCount is not None and len(keep) >= maxCount:
            break
        if imgId not in coco.anns:
            continue
        annIds = coco.getAnnIds(imgIds=[imgId])
        annotations = coco.loadAnns(ids=annIds)
        valid_annotations = [annotation for annotation in annotations
                if annotation['area'] >= areaConstraint[0] and annotation['area'] <= areaConstraint[1]]
        if len(valid_annotations) > 0:
            keep.append(imgId)
            annotations_to_keep.extend(valid_annotations)
    dataset = {'info':coco.dataset['info'],
               'images':coco.loadImgs(ids=keep),
               'categories':coco.dataset['categories'],
               'annotations':annotations_to_keep}

    with open(filename, 'w') as f:
        json.dump(dataset, f, indent=2, encoding='utf-8')

def main(argv=None):
    createSubset('/Users/ericrobertson/Downloads/annotations/instances_train2014.json',
                 'tests/other_plugins/CocoMaskSelector/annotations.json',
                  maxCount=30)

if __name__ == "__main__":
    import sys
    sys.exit(main())