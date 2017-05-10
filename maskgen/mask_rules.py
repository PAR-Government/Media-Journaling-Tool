from tool_set import toIntTuple, alterMask, alterReverseMask
import exif
import graph_rules
from image_wrap import ImageWrapper
from group_filter import getOperationWithGroups
from software_loader import Operation
import tool_set
import numpy as np
import cv2
import logging

def recapture_transform(edge, source, target, edgeMask,
                        compositeMask=None,
                        directory='.',
                        level=None,
                        donorMask=None,
                        pred_edges=None,
                        graph=None):
    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    tm = edge['transform matrix'] if 'transform matrix' in edge  else None
    position_str = edge['arguments']['Position Mapping'] if 'arguments' in edge and \
                   edge['arguments'] is not None and \
                   'Position Mapping' in edge['arguments'] else None
    if position_str is not None and len(position_str) > 0:
        parts = position_str.split(':')
        left_box = tool_set.coordsFromString(parts[0])
        right_box = tool_set.coordsFromString(parts[1])
        angle = int(float(parts[2]))
        if compositeMask is not None:
            res = compositeMask
            expectedSize = (res.shape[0] + sizeChange[0], res.shape[1] + sizeChange[1])
            expectedPasteSize = ((right_box[3]-right_box[1]),(right_box[2]-right_box[0]))
            newMask = np.zeros(expectedSize)
            clippedMask = res[left_box[1]:left_box[3],left_box[0]:left_box[2]]
            angleFactor = round(float(angle)/90.0)
            if abs(angleFactor) > 0:
                res = np.rot90(clippedMask, int(angleFactor)).astype('uint8')
                angle = angle - int(angleFactor*90)
            else:
                res = clippedMask
            res = tool_set.applyResizeComposite(res, (expectedPasteSize[0], expectedPasteSize[1]))
            if right_box[3] > newMask.shape[0] and right_box[2] > newMask.shape[1]:
                logging.getLogger('maskgen').warning('The mask for recapture edge with file {} has an incorrect size'.format(edge['maskname']))
                newMask = np.resize(newMask, (right_box[3] + 1, right_box[2] + 1))
            newMask[right_box[1]:right_box[3],right_box[0]:right_box[2]] = res
            if angle!=0:
                center = (right_box[1] + (right_box[3] -right_box[1]) / 2, right_box[0] + (right_box[2] - right_box[0]) / 2)
                res = tool_set.applyRotateToCompositeImage(newMask,angle,center)
            else:
                res = newMask.astype('uint8')
            return res
        elif donorMask is not None:
            res = donorMask
            expectedSize = (res.shape[0] + sizeChange[0], res.shape[1] + sizeChange[1])
            targetSize = edgeMask.shape if edgeMask is not None else expectedSize
            expectedPasteSize = ((left_box[3] - left_box[1]), (left_box[2] - left_box[0]))
            newMask = np.zeros(targetSize)
            ninetyRotate = 0
            angleFactor = round(float(angle) / 90.0)
            if abs(angleFactor) > 0:
                res = ninetyRotate= int(angleFactor)
                angle = angle - int(angleFactor*90)
            if angle != 0:
                center = (
                    right_box[1] + (right_box[3] - right_box[1]) / 2, right_box[0] + (right_box[2] - right_box[0]) / 2)
                res = tool_set.applyRotateToCompositeImage(res, -angle, center)
            clippedMask = res[right_box[1]:right_box[3], right_box[0]:right_box[2]]
            if ninetyRotate != 0:
                clippedMask = np.rot90(clippedMask, -ninetyRotate).astype('uint8')
            res = tool_set.applyResizeComposite(clippedMask, (expectedPasteSize[0], expectedPasteSize[1]))
            newMask[left_box[1]:left_box[3], left_box[0]:left_box[2]] = res
            return res

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
                                          mask=edgeMask,
                                          transform_matrix=tool_set.deserializeMatrix(tm),
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


def resize_transform(edge, source, target,edgeMask,
                     compositeMask=None,
                     directory='.',
                     level=None,
                     donorMask=None,
                     pred_edges=None,
                     graph=None):
    import os
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
            upperBound = (min(res.shape[0] + location[0], newRes.shape[0]),
                          min(res.shape[1] + location[1]),newRes.shape[1])
            newRes[location[0]:upperBound[0], location[1]:upperBound[1]] = res[0:(upperBound[0] - location[0]),
                                                                           0:(upperBound[1] - location[1])]
            res = newRes
        elif sizeChange == (0, 0):
            if tm is not None:
                # local resize
                res = tool_set.applyTransformToComposite(res, edgeMask, tool_set.deserializeMatrix(tm))
            elif 'inputmaskname' in edge and edge['inputmaskname'] is not None:
                inputmask = tool_set.openImageFile(os.path.join(directory, edge['inputmaskname']))
                if inputmask is not None:
                    mask = inputmask.to_mask().to_array()
                    res = move_pixels(mask,255-edgeMask, res,isComposite=True)
        if expectedSize != res.shape:
            res = tool_set.applyResizeComposite(res, (expectedSize[0], expectedSize[1]))
        return res
    elif donorMask is not None:
        res = donorMask
        expectedSize = (res.shape[0] - sizeChange[0], res.shape[1] - sizeChange[1])
        targetSize = edgeMask.shape if edgeMask is not None else expectedSize
        if canvas_change:
            upperBound = (
                min(expectedSize[0] + location[0], res.shape[0]), min(expectedSize[1] + location[1], res.shape[1]))
            res = res[location[0]:upperBound[0], location[1]:upperBound[1]]
        elif sizeChange == (0, 0):
            if tm is not None:
                res = tool_set.applyTransform(res, mask=edgeMask, transform_matrix=tool_set.deserializeMatrix(tm), invert=True, returnRaw=False)
            elif 'inputmaskname' in edge and edge['inputmaskname'] is not None:
                inputmask = tool_set.openImageFile(os.path.join(directory, edge['inputmaskname']))
                if inputmask is not None:
                    mask = inputmask.to_mask().to_array()
                    res = move_pixels(255-edgeMask, mask, res)
        if targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res
    return edgeMask

def select_remove(edge, source, target,edgeMask,
                     compositeMask=None,
                     directory='.',
                     level=None,
                     donorMask=None,
                     pred_edges=None,
                     graph=None):
    sizeChange = (0, 0)
    if 'shape change' in edge:
        changeTuple = toIntTuple(edge['shape change'])
        sizeChange = (changeTuple[0], changeTuple[1])
    location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0, 0)
    if location != (0, 0):
        sizeChange = (-location[0], -location[1]) if sizeChange == (0, 0) else sizeChange
    if compositeMask is not None:
        expectedSize = (compositeMask.shape[0] + sizeChange[0], compositeMask.shape[1] + sizeChange[1])
        res = tool_set.applyMask(compositeMask, edgeMask)
        if expectedSize != res.shape:
            res = tool_set.applyResizeComposite(res, (expectedSize[0], expectedSize[1]))
        return res
    else:
        targetSize = edgeMask.shape if edgeMask is not None else (0, 0)
        res = donorMask
        # res is the donor mask
        # edgeMask may be the overriding mask from a PasteSplice, thus in the same shape
        # The transfrom will convert to the target mask size of the donor path.
        #res = tool_set.applyMask(donorMask, edgeMask)
        if targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res

def crop_transform(edge, source, target,edgeMask,
                   compositeMask=None,
                   directory='.',
                   level=None,
                   donorMask=None,
                   pred_edges=None,
                   graph=None):
    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0, 0)
    sizeChange = (-location[0], -location[1]) if location != (0, 0) and sizeChange == (0, 0) else sizeChange
    if compositeMask is not None:
        res = compositeMask
        expectedSize = (res.shape[0] + sizeChange[0], res.shape[1] + sizeChange[1])
        upperBound = ( min(res.shape[0], expectedSize[0] + location[0]),
                       min(res.shape[1], expectedSize[1] + location[1]))
        res = res[location[0]:upperBound[0], location[1]:upperBound[1]]
        return res
    elif donorMask is not None:
        res = donorMask
        expectedSize = (res.shape[0]-sizeChange[0], res.shape[1] - sizeChange[1])
        newRes = np.zeros(expectedSize).astype('uint8')
        targetSize = edgeMask.shape if edgeMask is not None else expectedSize
        upperBound = (res.shape[0] + location[0], res.shape[1] + location[1])
        newRes[location[0]:upperBound[0], location[1]:upperBound[1]] = res[0:(upperBound[0] - location[0]),
                                                                       0:(upperBound[1] - location[1])]
        res = newRes
        if targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res
    return edgeMask


def seam_transform(edge,
                   source,
                   target,
                   edgeMask,
                   compositeMask=None,
                   directory='.',
                   level=None,
                   donorMask=None,
                   pred_edges=None,
                   graph=None):
    targetImage = graph.get_image(target)[0]
    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    args = edge['arguments'] if 'arguments' in edge else {}
    #if 'skip'
    matchx = sizeChange[0] == 0
    matchy = sizeChange[1] == 0
    res = None
    transformMatrix = tool_set.deserializeMatrix(edge['transform matrix']) if 'transform matrix' in edge  else None
    if (matchx and not matchy) or (not matchx and matchy):
        if compositeMask is not None:
            expectedSize = (targetImage.size[1], targetImage.size[0])
            res = tool_set.carveMask(compositeMask, edgeMask, expectedSize)
        else:
            # Need to think through this some more.
            # Seam carving essential puts pixels back.
            # perhaps this is ok, since the resize happens first and then the cut of the removed pixels
            targetSize = edgeMask.shape
            res = tool_set.applyMask(donorMask, edgeMask)
            if transformMatrix is not None:
                res = cv2.warpPerspective(res, transformMatrix, (targetSize[1], targetSize[0]),
                                          flags=cv2.WARP_INVERSE_MAP,
                                          borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype('uint8')
            # need to use target size since the expected does ot align with the donor paths.
            if targetSize != res.shape:
                res = cv2.resize(res, (targetSize[1], targetSize[0]))

    else:
        res = tool_set.applyInterpolateToCompositeImage(compositeMask if compositeMask is not None else donorMask,
                                              graph.get_image(source)[0],
                                                   targetImage,
                                              inverse=donorMask is not None,
                                              arguments=edge['arguments'] if 'arguments' in edge else {},
                                              defaultTransform=transformMatrix)
    if res is None or len(np.unique(res)) == 1:
        return defaultMaskTransform(edge,
                                    source,
                                    target,
                                    edgeMask,
                                    compositeMask=compositeMask,
                                    directory=directory,
                                    level=level,
                                    donorMask=donorMask,
                                    pred_edges=pred_edges,
                                    graph=graph)
    return res

def cas_transform(edge,
                   source,
                   target,
                   edgeMask,
                   compositeMask=None,
                   directory='.',
                   level=None,
                   donorMask=None,
                   pred_edges=None,
                   graph=None):
    res = None
    tm = tool_set.deserializeMatrix(edge['transform matrix']) if 'transform matrix' in edge  else None
    if compositeMask is not None:
        targetImage = graph.get_image(target)[0]
        res = tool_set.applyInterpolateToCompositeImage(compositeMask,
                                              graph.get_image(source)[0],
                                              targetImage,
                                              inverse=donorMask is not None,
                                              arguments=edge['arguments'] if 'arguments' in edge else {},
                                              defaultTransform=tm)
    if res is None or len(np.unique(res)) == 1:
        return defaultMaskTransform(edge,
                                    source,
                                    target,
                                    edgeMask,
                                    compositeMask=compositeMask,
                                    directory=directory,
                                    level=level,
                                    donorMask=donorMask,
                                    pred_edges=pred_edges,
                                    graph=graph)
    return res

def move_pixels(frommask, tomask, image, isComposite=False):
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

    if isComposite:
        transformedImage = tool_set.applyPerspectiveToComposite(image, M, tomask.shape)
        transformedImage = transformedImage.astype('uint8')
    else:
        transformedImage = cv2.warpPerspective(image, M, (tomask.shape[1], tomask.shape[0]))
        transformedImage = transformedImage.astype('uint8')
    return transformedImage

def move_transform(edge, source, target, edgeMask,
                   compositeMask=None,
                   directory='.',
                   level=None,
                   donorMask=None,
                   pred_edges=None,
                   graph=None):
    import os
    returnRaw = False
    try:
        returnRaw = True
        inputmask =  \
            tool_set.openImageFile(os.path.join(directory,edge['inputmaskname'])).to_mask().invert().to_array() \
            if 'inputmaskname' in edge and edge['inputmaskname'] is not None else edgeMask
    except:
        inputmask = edgeMask

    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    tm = edge['transform matrix'] if 'transform matrix' in edge  else None
    if compositeMask is not None:
        res = compositeMask
        expectedSize = (res.shape[0] + sizeChange[0], res.shape[1] + sizeChange[1])
        if inputmask.shape != res.shape:
            inputmask = cv2.resize(inputmask,(res.shape[1],res.shape[0]))
        if tm is not None:
            res = tool_set.applyTransformToComposite(res, inputmask, tool_set.deserializeMatrix(tm), returnRaw=returnRaw)
        else:
            inputmask = 255-inputmask
            differencemask = (255-edgeMask) - inputmask
            differencemask[differencemask<0] = 0
            res =move_pixels(inputmask,differencemask,res,isComposite=True)
        if expectedSize != res.shape:
            res = tool_set.applyResizeComposite(res, (expectedSize[0], expectedSize[1]))
        return res
    elif donorMask is not None:
        res = donorMask
        expectedSize = (res.shape[0] - sizeChange[0], res.shape[1] - sizeChange[1])
        targetSize = edgeMask.shape if edgeMask is not None else expectedSize
        if tm is not None:
            res = tool_set.applyTransform(res,
                                          mask=inputmask,
                                          transform_matrix=tool_set.deserializeMatrix(tm),
                                          invert=True,
                                          returnRaw=False)
        else:
            if inputmask.shape != edgeMask.shape:
                inputmask = cv2.resize(inputmask, (res.shape[1], res.shape[0]))
            inputmask = 255 - inputmask
            differencemask =  (255-edgeMask) - inputmask
            differencemask[differencemask < 0] = 0
            res = move_pixels(differencemask,inputmask,res)
        if targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res
    return edgeMask


def pastesplice(edge, source, target,edgeMask,
                compositeMask=None,
                directory='.',
                level=None,
                donorMask=None,
                pred_edges=None,
                graph=None):
    import os
    if compositeMask is not None:
        pastemask = edge['arguments']['pastemask'] if 'arguments' in edge and 'pastemask' in edge['arguments'] else None
        if pastemask is not None and os.path.exists (os.path.join(directory,pastemask)):
           inputmask =  tool_set.openImageFile(os.path.join(directory,pastemask)).to_mask().to_array()
           compositeMask[compositeMask == level]  = 0
           compositeMask[inputmask>0] = level
        return compositeMask
    else:
        donorMask = tool_set.applyMask(donorMask, edgeMask)
    return donorMask


def donor(edge, source, target, edgeMask,
          compositeMask=None,
          directory='.',
          level=None,
          donorMask=None,
          pred_edges=None,
          graph=None):
    if compositeMask is not None:
        return compositeMask
    else:
        # removed code to handle the paste splice issue where part of the donor
        # may NOT be used.  The old method tried a reverse transform of the
        # inverted paste splice edge mask, rather than using the  edge mask itself.
        # this only works IF there a transform matrix.
        # pred_edges would contain the paste splice mask
        # (edgeMask = edge['maskname']) to which can be use to zero out the
        # unchanged pixels and then apply a transform.
        if len([edge for edge in pred_edges if edge['recordMaskInComposite'] == 'yes']) > 0:
            tm = edge['transform matrix'] if 'transform matrix' in edge  else None
            targetSize = edgeMask.shape
            if tm is not None:
                donorMask = cv2.warpPerspective(donorMask, tool_set.deserializeMatrix(tm), (targetSize[1], targetSize[0]),
                                          flags=cv2.WARP_INVERSE_MAP,
                                          borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype('uint8')
            else:
                donorMask = ImageWrapper(edgeMask).invert().to_array()
        else:
            #donorMask = ImageWrapper(edgeMask).invert().to_array()
            donorMask = np.zeros(donorMask.shape,dtype=np.uint8)
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

def defaultAlterComposite(edge, edgeMask, compositeMask=None, directory='.', level=None,donorMask=None,pred_edges=None):
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
    crop = (sizeChange[0] < 0 or sizeChange[1] < 0) and tm is None and abs(rotation) < 0.00001
    flip = flip if flip is not None else orientflip
    tm = None if (cut or flip) else tm
    location = (0, 0) if tm and edge['op'] in [ 'Recapture']  else location
    crop = True if edge['op'] in ['Recapture'] else crop
    compositeMask = alterMask(compositeMask,
                              edgeMask,
                              rotation=rotation,
                              sizeChange=sizeChange,
                              interpolation=interpolation,
                              location=location,
                              flip=flip,
                              transformMatrix=tm,
                              crop=crop,
                              cut=cut)
    return compositeMask


def defaultAlterDonor(edge, edgeMask, compositeMask=None, directory='.', level=None,donorMask=None,pred_edges=None):
    targetSize = edgeMask.shape if edgeMask is not None else (0, 0)
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
    cut = edge['op'] in ('SelectRemove')
    crop = (sizeChange[0] < 0 or sizeChange[1] < 0) and tm is None and abs(rotation) < 0.00001
    flip = flip if flip is not None else orientflip
    tm = None if (cut or flip) else tm
    return alterReverseMask(donorMask,
                            edgeMask,
                            rotation=rotation,
                            sizeChange=sizeChange,
                            location=location,
                            flip=flip,
                            transformMatrix=tm,
                            targetSize=targetSize,
                            crop=crop,
                            cut=cut)

def defaultMaskTransform(edge,
                         source,
                         target,
                         edgeMask,
                         compositeMask=None,
                         directory='.',
                         level=None,
                         donorMask=None,
                         pred_edges=None,
                         graph=None):
    if compositeMask is not None:
        return defaultAlterComposite(edge, edgeMask, compositeMask=compositeMask,directory=directory,
                                     level=level,donorMask=None,pred_edges=pred_edges)
    else:
        return defaultAlterDonor(edge, edgeMask, compositeMask=None, directory=directory,
                              level=level, donorMask=donorMask, pred_edges=pred_edges)

def alterComposite(edge, source, target, compositeMask, edgeMask,directory,level=255,graph=None):
    op = getOperationWithGroups(edge['op'],fake=True)
    if op.maskTransformFunction is not None:
        return graph_rules.getRule(op.maskTransformFunction)(edge, source, target, edgeMask, level=level,
                                                             compositeMask=compositeMask,
                                                             directory=directory,
                                                             graph=graph)
    return defaultAlterComposite(edge, edgeMask,
                                 level=level,
                                 compositeMask=compositeMask,
                                 directory=directory)


def alterDonor(donorMask, source, target, edge, edgeMask,  directory='.',pred_edges=[],graph=None):
    """

    :param self:
    :param donorMask: The mask to alter and return
    :param source:
    :param target:
    :param edge: the edge the provides the instructions for alteration
    :return:
    """
    if donorMask is None:
        return None
    if edgeMask is None:
        raise ValueError('Missing edge mask from ' + source + ' to ' + target)

    edgeMask = edgeMask.to_array()
    op = getOperationWithGroups(edge['op'],fake=True)
    if op.maskTransformFunction is not None:
        return graph_rules.getRule(op.maskTransformFunction)(edge,
                                                             source,
                                                             target,
                                                             edgeMask,
                                                             directory=directory,
                                                             donorMask=donorMask,
                                                             pred_edges=pred_edges,
                                                             graph=graph)

    return defaultAlterDonor(edge, edgeMask, directory=directory,donorMask=donorMask,pred_edges=pred_edges)




