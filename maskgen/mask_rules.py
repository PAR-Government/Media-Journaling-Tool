from tool_set import toIntTuple, alterMask, alterReverseMask
import exif
import graph_rules
from image_wrap import ImageWrapper
from group_filter import getOperationWithGroups
from software_loader import Operation
import tool_set
import numpy as np
import cv2


def recapture_transform(edge, edgeMask, compositeMask=None, directory='.',level=None,donorMask=None, edgeSelection=None, overideMask=None):
    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    tm = edge['transform matrix'] if 'transform matrix' in edge  else None
    location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0, 0)
    if compositeMask is not None:
        res = compositeMask
        expectedSize = (res.shape[0] + sizeChange[0], res.shape[1] + sizeChange[1])
        if tm is not None:
            res = tool_set.applyTransformToComposite(res,
                                                     edgeMask,
                                                     tool_set.deserializeMatrix(tm),
                                                     shape=expectedSize,
                                                     returnRaw=True)
        #elif location != (0, 0):
        #    upperBound = (
        #        min(res.shape[0], location[0]+expectedSize[0]), min(res.shape[1], location[1]+expectedSize[1]))
        #    res = res[location[0]:upperBound[0], location[1]:upperBound[1]]
        elif expectedSize != res.shape:
            res = tool_set.applyResizeComposite(compositeMask, (expectedSize[0], expectedSize[1]))
        return res
    elif donorMask is not None:
        res = donorMask
        expectedSize = (res.shape[0] + sizeChange[0], res.shape[1] + sizeChange[1])
        if tm is not None:
            res = tool_set.applyTransform(res,
                                          edgeMask,
                                          tool_set.deserializeMatrix(tm),
                                          invert=True,
                                          shape=expectedSize,
                                          returnRaw=True)
        #elif location != (0, 0):
        #    newRes = np.zeros(expectedSize).astype('uint8')
        #    upperBound = (
        #        min(expectedSize[0] + location[0], res.shape[0]), min(expectedSize[1] + location[1], res.shape[1]))
        #    newRes[location[0]:upperBound[0], location[1]:upperBound[1]] = res[0:(upperBound[0] - location[0]),
        #                                                                   0:(upperBound[1] - location[1])]
        #    res = newRes
        elif expectedSize != res.shape:
            res = tool_set.applyResizeComposite(res, (expectedSize[0], expectedSize[1]))
        return res
    return edgeMask


def resize_transform(edge, edgeMask, compositeMask=None,directory='.', level=None,donorMask=None, edgeSelection=None, overideMask=None):
    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0, 0)
    args = edge['arguments'] if 'arguments' in edge else {}
    canvas_change = (sizeChange != (0, 0) and 'interpolation' in args and 'none' == args['interpolation'].lower())
    tm = edge['transform matrix'] if 'transform matrix' in edge  else None
    if location != (0, 0):
        sizeChange = (-location[0], -location[1]) if sizeChange == (0, 0) else sizeChange
    if compositeMask is not None:
        res = compositeMask
        expectedSize = (res.shape[0] + sizeChange[0], res.shape[1] + sizeChange[1])
        if canvas_change:
            newRes = np.zeros(expectedSize).astype('uint8')
            upperBound = (res.shape[0] + location[0], res.shape[1] + location[1])
            newRes[location[0]:upperBound[0], location[1]:upperBound[1]] = res[0:(upperBound[0] - location[0]),
                                                                           0:(upperBound[1] - location[1])]
            res = newRes
        elif sizeChange == (0, 0) and tm is not None:
            # local resize
            res = tool_set.applyTransformToComposite(res, edgeMask, tool_set.deserializeMatrix(tm))
        if expectedSize != res.shape:
            res = tool_set.applyResizeComposite(res, (expectedSize[0], expectedSize[1]))
        return res
    elif donorMask is not None:
        res = donorMask
        edgeMask = overideMask if overideMask is not None else edgeMask
        expectedSize = (res.shape[0] - sizeChange[0], res.shape[1] - sizeChange[1])
        targetSize = edgeMask.shape if edgeMask is not None else expectedSize
        if canvas_change:
            upperBound = (
                min(expectedSize[0] + location[0], res.shape[0]), min(expectedSize[1] + location[1], res.shape[1]))
            res = res[location[0]:upperBound[0], location[1]:upperBound[1]]
        elif sizeChange == (0, 0) and tm is not None:
            res = tool_set.applyTransform(res, edgeMask, tool_set.deserializeMatrix(tm), invert=True, returnRaw=False)
        if targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res
    return edgeMask

def move_pixels(frommask, tomask, image):
    lowerm, upperm = tool_set.boundingRegion(frommask)
    lowerd, upperd = tool_set.boundingRegion(tomask)
    M = cv2.getPerspectiveTransform(np.asarray([[lowerm[0], lowerm[1]],
                                                [upperm[0], lowerm[1]],
                                                [upperm[0], upperm[1]],
                                                [lowerm[0], upperm[1]]]
                                                ).astype(
        'float32'),
                                    np.asarray([[lowerd[0], lowerd[1]],
                                                [upperd[0], lowerd[1]],
                                                [upperd[0], upperd[1]],
                                                [lowerd[0], upperd[1]]]).astype(
                                        'float32'))
    newimage = image*50
    transformedImage = cv2.warpPerspective(newimage, M, (tomask.shape[1], tomask.shape[0]))
    transformedImage = (transformedImage/50).astype('uint8')
    return transformedImage

def move_transform(edge, edgeMask, compositeMask=None, directory='.', level=None,donorMask=None, edgeSelection=None, overideMask=None):
    import os
    inputmask =  \
        tool_set.openImageFile(os.path.join(directory,edge['inputmaskname'])).to_mask().invert().to_array() \
        if 'inputmaskname' in edge else edgeMask

    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    tm = edge['transform matrix'] if 'transform matrix' in edge  else None
    if compositeMask is not None:
        res = compositeMask
        expectedSize = (res.shape[0] + sizeChange[0], res.shape[1] + sizeChange[1])
        if inputmask.shape != res.shape:
            inputmask = cv2.resize(inputmask,(res.shape[1],res.shape[0]))
        if tm is not None:
            res = tool_set.applyTransformToComposite(res, inputmask, tool_set.deserializeMatrix(tm))
        else:
            inputmask = 255-inputmask
            differencemask = (255-edgeMask) - inputmask
            differencemask[differencemask<0] = 0
            res =move_pixels(inputmask,differencemask,res)
        if expectedSize != res.shape:
            res = tool_set.applyResizeComposite(res, (expectedSize[0], expectedSize[1]))
        return res
    elif donorMask is not None:
        res = donorMask
        expectedSize = (res.shape[0] - sizeChange[0], res.shape[1] - sizeChange[1])
        targetSize = edgeMask.shape if edgeMask is not None else expectedSize
        if tm is not None:
            res = tool_set.applyTransform(res, inputmask, tool_set.deserializeMatrix(tm),invert=True, returnRaw=False)
        else:
            inputmask = 255 - inputmask
            differencemask =  (255-edgeMask) - inputmask
            differencemask[differencemask < 0] = 0
            res = move_pixels(differencemask,inputmask,res)
        if targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res
    return edgeMask


def pastesplice(edge, edgeMask, compositeMask=None, directory='.', level=None,donorMask=None, edgeSelection=None, overideMask=None):
    import os
    if compositeMask is not None:
        pastemask = edge['arguments']['pastemask'] if 'arguments' in edge and 'pastemask' in edge['arguments'] else None
        if pastemask is not None and os.path.exists (os.path.join(directory,pastemask)):
           inputmask =  tool_set.openImageFile(os.path.join(directory,pastemask)).to_mask().to_array()
           compositeMask[compositeMask == level]  = 0
           compositeMask[inputmask>0] = level
        return compositeMask
    return donorMask

def _getOrientation(edge):
    if ('arguments' in edge and \
                ('Image Rotated' in edge['arguments'] and \
                             edge['arguments']['Image Rotated'] == 'yes')) and \
                    'exifdiff' in edge and 'Orientation' in edge['exifdiff']:
        return edge['exifdiff']['Orientation'][1]
    if ('arguments' in edge and \
                ('rotate' in edge['arguments'] and \
                             edge['arguments']['rotate'] == 'yes')) and \
                    'exifdiff' in edge and 'Orientation' in edge['exifdiff']:
        return edge['exifdiff']['Orientation'][2] if edge['exifdiff']['Orientation'][0].lower() == 'change' else \
            edge['exifdiff']['Orientation'][1]
    return ''


def alterComposite(edge, compositeMask, edgeMask,directory,level=255):
    op = getOperationWithGroups(edge['op'],fake=True)
    if op.maskTransformFunction is not None:
        return graph_rules.getRule(op.maskTransformFunction)(edge, edgeMask, level=level,compositeMask=compositeMask,directory=directory)

    # change the mask to reflect the output image
    # considering the crop again, the high-lighted change is not dropped
    # considering a rotation, the mask is now rotated
    sizeChange = (0, 0)
    if 'shape change' in edge:
        changeTuple = toIntTuple(edge['shape change'])
        sizeChange = (changeTuple[0], changeTuple[1])
    location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0, 0)
    rotation = float(edge['rotation'] if 'rotation' in edge and edge['rotation'] is not None else 0.0)
    args = edge['arguments'] if 'arguments' in edge else {}
    rotation = float(args['rotation'] if 'rotation' in args and args['rotation'] is not None else rotation)
    interpolation = args['interpolation'] if 'interpolation' in args and len(
        args['interpolation']) > 0 else 'nearest'
    tm = edge['transform matrix'] if 'transform matrix' in edge  else None
    flip = args['flip direction'] if 'flip direction' in args else None
    orientflip, orientrotate = exif.rotateAmount(_getOrientation(edge))
    rotation = rotation if rotation is not None and abs(rotation) > 0.00001 else orientrotate
    tm = None if ('global' in edge and edge['global'] == 'yes' and rotation != 0.0) else tm
    cut = edge['op'] in ('SelectRemove')
    carve, tm, edgeMask = graph_rules.seamCarvingAlterations(edge, tm, edgeMask)
    crop = sizeChange != (0, 0) and \
           (edge['op'] == 'TransformCrop' or (edge['op'] == 'TransformSeamCarving' and not carve and tm is None))
    flip = flip if flip is not None else orientflip
    global_resize = (sizeChange != (0, 0) and edge['op'] not in ['TransformSeamCarving', 'Recapture'])
    tm = None if (crop or cut or flip or carve or global_resize) else tm
    location = (0, 0) if tm and edge['op'] in ['TransformSeamCarving', 'Recapture']  else location
    crop = True if edge['op'] in ['TransformSeamCarving', 'Recapture'] else crop
    compositeMask = alterMask(compositeMask,
                              edgeMask,
                              rotation=rotation,
                              sizeChange=sizeChange,
                              interpolation=interpolation,
                              location=location,
                              flip=flip,
                              transformMatrix=tm,
                              crop=crop,
                              cut=cut,
                              carve=carve)
    return compositeMask


def alterDonor(donorMask, source, target, edge, edgeMask, edgeSelection=None, overideMask=None, directory='.'):
    """

    :param self:
    :param donorMask: The mask to alter and return
    :param source:
    :param target:
    :param edge: the edge the provides the instructions for alteration
    :param edgeSelection:
    :param overideMask:
    :return:
    """
    if donorMask is None:
        return None
    if edgeMask is None:
        raise ValueError('Missing edge mask from ' + source + ' to ' + target)

    edgeMask = edgeMask.to_array()
    op = getOperationWithGroups(edge['op'],fake=True)
    if op.maskTransformFunction is not None:
        return graph_rules.getRule(op.maskTransformFunction)(edge, edgeMask, directory=directory,donorMask=donorMask,
                                                             edgeSelection=edgeSelection, overideMask=overideMask)

    targetSize = edgeMask.shape if edgeMask is not None else (0, 0)
    edgeMask = overideMask if overideMask is not None else edgeMask
    # change the mask to reflect the output image
    # considering the crop again, the high-lighted change is not dropped
    # considering a rotation, the mask is now rotated
    sizeChange = (0, 0)
    if 'shape change' in edge:
        changeTuple = toIntTuple(edge['shape change'])
        sizeChange = (changeTuple[0], changeTuple[1])
    location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0, 0)
    rotation = float(edge['rotation'] if 'rotation' in edge and edge['rotation'] is not None else 0.0)
    args = edge['arguments'] if 'arguments' in edge else {}
    rotation = float(args['rotation'] if 'rotation' in args and args['rotation'] is not None else rotation)
    tm = edge['transform matrix'] if 'transform matrix' in edge  else None
    flip = args['flip direction'] if 'flip direction' in args else None
    orientflip, orientrotate = exif.rotateAmount(_getOrientation(edge))
    orientrotate = -orientrotate if orientrotate is not None else None
    rotation = rotation if rotation is not None and abs(rotation) > 0.00001 else orientrotate
    tm = None if ('global' in edge and edge['global'] == 'yes' and rotation != 0.0) else tm
    cut = edge['op'] in ('SelectRemove') or edgeSelection is not None
    edgeMask = ImageWrapper(edgeMask).invert().to_array() if edgeSelection == 'invert' else edgeMask
    carve, tm, edgeMask = graph_rules.seamCarvingAlterations(edge, tm, edgeMask)
    cut = carve or cut
    crop = sizeChange != (0, 0) and (
        edge['op'] == 'TransformCrop' or (edge['op'] == 'TransformSeamCarving' and not carve and tm is None))
    flip = flip if flip is not None else orientflip
    global_resize = (sizeChange != (0, 0) and edge['op'] != 'TransformSeamCarving')
    tm = None if (crop or cut or flip or carve or global_resize) else tm
    return alterReverseMask(donorMask, edgeMask,
                            rotation=rotation,
                            sizeChange=sizeChange,
                            location=location,
                            flip=flip,
                            transformMatrix=tm,
                            targetSize=targetSize,
                            crop=crop,
                            cut=cut)
