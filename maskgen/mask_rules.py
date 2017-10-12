from tool_set import toIntTuple, alterMask, alterReverseMask, shortenName, openImageFile, sizeOfChange, convertToMask
import exif
import graph_rules
from image_wrap import ImageWrapper
import tool_set
import numpy as np
import cv2
import logging
from image_graph import ImageGraph
import os
from maskgen import Probe


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
            expectedPasteSize = ((right_box[3] - right_box[1]), (right_box[2] - right_box[0]))
            newMask = np.zeros(expectedSize)
            clippedMask = res[left_box[1]:left_box[3], left_box[0]:left_box[2]]
            angleFactor = round(float(angle) / 90.0)
            if abs(angleFactor) > 0:
                res = np.rot90(clippedMask, int(angleFactor)).astype('uint8')
                angle = angle - int(angleFactor * 90)
            else:
                res = clippedMask
            res = tool_set.applyResizeComposite(res, (expectedPasteSize[0], expectedPasteSize[1]))
            if right_box[3] > newMask.shape[0] and right_box[2] > newMask.shape[1]:
                logging.getLogger('maskgen').warning(
                    'The mask for recapture edge with file {} has an incorrect size'.format(edge['maskname']))
                newMask = np.resize(newMask, (right_box[3] + 1, right_box[2] + 1))
            newMask[right_box[1]:right_box[3], right_box[0]:right_box[2]] = res
            if angle != 0:
                center = (
                right_box[1] + (right_box[3] - right_box[1]) / 2, right_box[0] + (right_box[2] - right_box[0]) / 2)
                res = tool_set.applyRotateToCompositeImage(newMask, angle, center)
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
                res = ninetyRotate = int(angleFactor)
                angle = angle - int(angleFactor * 90)
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
        # elif location != (0, 0):
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
        # elif location != (0, 0):
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


def resize_transform(edge, source, target, edgeMask,
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
                          min(res.shape[1] + location[1]), newRes.shape[1])
            newRes[location[0]:upperBound[0], location[1]:upperBound[1]] = res[0:(upperBound[0] - location[0]),
                                                                           0:(upperBound[1] - location[1])]
            res = newRes
        elif sizeChange == (0, 0):
            if tm is not None:
                # local resize
                res = tool_set.applyTransformToComposite(res, edgeMask, tool_set.deserializeMatrix(tm))
            elif 'inputmaskname' in edge and edge['inputmaskname'] is not None:
                inputmask = openImageFile(os.path.join(directory, edge['inputmaskname']))
                if inputmask is not None:
                    mask = inputmask.to_mask().to_array()
                    res = move_pixels(mask, 255 - edgeMask, res, isComposite=True)
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
                res = tool_set.applyTransform(res, mask=edgeMask, transform_matrix=tool_set.deserializeMatrix(tm),
                                              invert=True, returnRaw=False)
            elif 'inputmaskname' in edge and edge['inputmaskname'] is not None:
                inputmask = openImageFile(os.path.join(directory, edge['inputmaskname']))
                if inputmask is not None:
                    mask = inputmask.to_mask().to_array()
                    res = move_pixels(255 - edgeMask, mask, res)
        if targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res
    return edgeMask


def rotate_transform(edge, source, target, edgeMask,
                     compositeMask=None,
                     directory='.',
                     level=None,
                     donorMask=None,
                     pred_edges=None,
                     graph=None):
    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    args = edge['arguments'] if 'arguments' in edge else {}
    rotation = float(args['rotation'] if 'rotation' in args and args['rotation'] is not None else 0)
    tm = edge['transform matrix'] if 'transform matrix' in edge  else None
    rotation = rotation if rotation is not None and abs(rotation) > 0.00001 else 0
    if sizeChange != (0, 0) and abs(int(round(rotation))) % 90 == 0:
        tm = None
    if donorMask is not None:
        if tm is not None:
            res = tool_set.applyTransform(donorMask, mask=edgeMask, transform_matrix=tool_set.deserializeMatrix(tm),
                                          invert=True,
                                          returnRaw=False)
        else:
            targetSize = edgeMask.shape if edgeMask is not None else (0, 0)
            res = tool_set.__rotateImage(-rotation, donorMask, expectedDims=targetSize, cval=0)
    else:
        expectedSize = (compositeMask.shape[0] + sizeChange[0], compositeMask.shape[1] + sizeChange[1])
        if tm is not None:
            res = tool_set.applyTransformToComposite(compositeMask, edgeMask, tool_set.deserializeMatrix(tm))
        else:
            res = tool_set.applyRotateToComposite(rotation, compositeMask,
                                                  (compositeMask.shape[0] + sizeChange[0],
                                                   compositeMask.shape[1] + sizeChange[1]))
        if expectedSize != res.shape:
            res = tool_set.applyResizeComposite(res, (expectedSize[0], expectedSize[1]))
    return res


def select_remove(edge, source, target, edgeMask,
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
        # res = tool_set.applyMask(donorMask, edgeMask)
        if targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res


def crop_transform(edge, source, target, edgeMask,
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
        upperBound = (min(res.shape[0], expectedSize[0] + location[0]),
                      min(res.shape[1], expectedSize[1] + location[1]))
        res = res[location[0]:upperBound[0], location[1]:upperBound[1]]
        return res
    elif donorMask is not None:
        res = donorMask
        expectedSize = (res.shape[0] - sizeChange[0], res.shape[1] - sizeChange[1])
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
    # if 'skip'
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
                                                        edgeMask,
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


def warp_transform(edge,
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
    if compositeMask is not None:
        tm = tool_set.deserializeMatrix(edge['transform matrix']) if 'transform matrix' in edge  else None
        res = tool_set.applyInterpolateToCompositeImage(compositeMask,
                                                        graph.get_image(source)[0],
                                                        graph.get_image(target)[0],
                                                        edgeMask,
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
                                                        edgeMask,
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
    # if lowerm == lowerd:
    #    M = cv2.getAffineTransform(np.asarray([
    #                                                [upperm[0], lowerm[1]],
    #                                                [upperm[0], upperm[1]],
    #                                                [lowerm[0], upperm[1]]]
    #                                               ).astype(
    #        'float32'),
    #       np.asarray([
    #                   [upperd[0], lowerd[1]],
    #                   [upperd[0], upperd[1]],
    #                    [lowerd[0], upperd[1]]]).astype(
    #            'float32'))
    #    if isComposite:
    #        transformedImage = tool_set.applyAffineToComposite(image, M, tomask.shape)
    #        transformedImage = transformedImage.astype('uint8')
    #    else:
    #        transformedImage = cv2.warpAffine(image, M, (tomask.shape[1], tomask.shape[0]))
    #        transformedImage = transformedImage.astype('uint8')
    #    return transformedImage

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
        # returnRaw = True
        inputmask = \
            openImageFile(os.path.join(directory, edge['inputmaskname'])).to_mask().invert().to_array() \
                if 'inputmaskname' in edge and edge['inputmaskname'] is not None else edgeMask
        # cdf29bf86e41c26c1247aa7952338ac0
        # 25% seems arbitrary.  How much overlap is needed before the inputmask stops providing useful information?
        decision = __getInputMaskDecision(edge)
        if decision == 'no' or \
                (decision != 'yes' and \
                                 sum(sum(abs(((255 - edgeMask) - (255 - inputmask)) / 255))) / float(
                                 sum(sum((255 - edgeMask) / 255))) <= 0.25):
            inputmask = edgeMask
    except:
        inputmask = edgeMask

    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    tm = edge['transform matrix'] if 'transform matrix' in edge  else None
    if compositeMask is not None:
        res = compositeMask
        expectedSize = (res.shape[0] + sizeChange[0], res.shape[1] + sizeChange[1])
        if inputmask.shape != res.shape:
            inputmask = cv2.resize(inputmask, (res.shape[1], res.shape[0]))
        if tm is not None:
            res = tool_set.applyTransformToComposite(res, inputmask, tool_set.deserializeMatrix(tm),
                                                     returnRaw=returnRaw)
        else:
            inputmask = 255 - inputmask
            differencemask = (255 - edgeMask) - inputmask
            differencemask[differencemask < 0] = 0
            res = move_pixels(inputmask, differencemask, res, isComposite=True)
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
            differencemask = (255 - edgeMask) - inputmask
            differencemask[differencemask < 0] = 0
            res = move_pixels(differencemask, inputmask, res)
        if targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res
    return edgeMask


def pastesplice(edge, source, target,
                edgeMask,
                compositeMask=None,
                directory='.',
                level=None,
                donorMask=None,
                pred_edges=None,
                graph=None):
    import os
    if compositeMask is not None:
        # pastemask = edge['arguments']['pastemask'] if 'arguments' in edge and 'pastemask' in edge['arguments'] else None
        # if top and pastemask is not None and os.path.exists (os.path.join(directory,pastemask)):
        #   inputmask =  tool_set.openImageFile(os.path.join(directory,pastemask)).to_mask().to_array()
        #   compositeMask[compositeMask == level]  = 0
        #   compositeMask[inputmask>0] = level
        return compositeMask
    else:
        # during a paste splice, the edge mask can split up the donor.
        # although I am wondeing if the edgemask needs to be inverted.
        # this effectively sets the donorMask pixels to 0 where the edge mask is 0 (which is 'changed')
        donorMask = tool_set.applyMask(donorMask, edgeMask)
    return donorMask


def donor(edge, source, target, edgeMask,
          compositeMask=None,
          directory='.',
          level=None,
          donorMask=None,
          pred_edges=None,
          graph=None,
          top=False
          ):
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
                donorMask = cv2.warpPerspective(donorMask, tool_set.deserializeMatrix(tm),
                                                (targetSize[1], targetSize[0]),
                                                flags=cv2.WARP_INVERSE_MAP,
                                                borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype('uint8')
            else:
                donorMask = ImageWrapper(edgeMask).invert().to_array()
        else:
            # donorMask = ImageWrapper(edgeMask).invert().to_array()
            donorMask = np.zeros(donorMask.shape, dtype=np.uint8)
    return donorMask


def __getInputMaskDecision(edge):
    tag = "use input mask for composites"
    if ('arguments' in edge and \
                (tag in edge['arguments'])):
        return edge['arguments']['tag']
    return None


def __getOrientation(edge):
    if ('arguments' in edge and \
                ('Image Rotated' in edge['arguments'] and \
                             edge['arguments']['Image Rotated'] == 'yes')) and \
                    'exifdiff' in edge and 'Orientation' in edge['exifdiff']:
        return edge['exifdiff']['Orientation'][1]
    if ('arguments' in edge and \
                ('rotate' in edge['arguments'] and \
                             edge['arguments']['rotate'] == 'yes')):
        if 'exifdiff' in edge and 'Orientation' in edge['exifdiff']:
            return edge['exifdiff']['Orientation'][2] if edge['exifdiff']['Orientation'][0].lower() == 'change' else \
                edge['exifdiff']['Orientation'][1]
        else:
            return graph_rules.getOrientationFromMetaData(edge)
    return ''


def defaultAlterComposite(edge, edgeMask, compositeMask=None, directory='.', level=None, donorMask=None,
                          pred_edges=None):
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
    orientflip, orientrotate = exif.rotateAmount(graph_rules.getOrientationForEdge(edge))
    rotation = rotation if rotation is not None and abs(rotation) > 0.00001 else orientrotate
    tm = None if ('global' in edge and edge['global'] == 'yes' and rotation != 0.0) else tm
    cut = edge['op'] in ('SelectRemove')
    crop = (sizeChange[0] < 0 or sizeChange[1] < 0) and tm is None and abs(rotation) < 0.00001
    flip = flip if flip is not None else orientflip
    tm = None if (cut or flip) else tm
    location = (0, 0) if tm and edge['op'] in ['Recapture']  else location
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


def defaultAlterDonor(edge, edgeMask, compositeMask=None, directory='.', level=None, donorMask=None, pred_edges=None):
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
    orientflip, orientrotate = exif.rotateAmount(graph_rules.getOrientationForEdge(edge))
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
        return defaultAlterComposite(edge, edgeMask, compositeMask=compositeMask, directory=directory,
                                     level=level, donorMask=None, pred_edges=pred_edges)
    else:
        return defaultAlterDonor(edge, edgeMask, compositeMask=None, directory=directory,
                                 level=level, donorMask=donorMask, pred_edges=pred_edges)


def alterDonor(donorMask, op, source, target, edge, edgeMask, directory='.', pred_edges=[], graph=None):
    """

    :param donorMask:
    :param op:  operation name
    :param source:
    :param target:
    :param edge: edge dictionary
    :param edgeMask:  composite
    :param directory:
    :param pred_edges:
    :param graph:
    :return:
    """
    if donorMask is None:
        return None
    if edgeMask is None:
        raise ValueError('Missing edge mask from ' + source + ' to ' + target)

    edgeMask = edgeMask.to_array()
    if op.maskTransformFunction is not None:
        return graph_rules.getRule(op.maskTransformFunction)(edge,
                                                             source,
                                                             target,
                                                             edgeMask,
                                                             directory=directory,
                                                             donorMask=donorMask,
                                                             pred_edges=pred_edges,
                                                             graph=graph)

    return defaultAlterDonor(edge, edgeMask, directory=directory, donorMask=donorMask, pred_edges=pred_edges)

def _getUnresolvedSelectMasksForEdge(edge):
    """
    A selectMask is a mask the is used in composite mask production, overriding the default link mask
    @rtype: dict
    """
    images = edge['selectmasks'] if 'selectmasks' in edge  else []
    sms = {}
    for image in images:
        sms[image['node']] = image['mask']
    return sms


def findBaseNodesWithCycleDetection(graph, node, excludeDonor=True):
    preds = graph.predecessors(node)
    res = [(node, 0, list())] if len(preds) == 0 else list()
    for pred in preds:
        if graph.get_edge(pred, node)['op'] == 'Donor' and excludeDonor:
            continue
        for item in findBaseNodesWithCycleDetection(graph,pred, excludeDonor=excludeDonor):
            res.append((item[0], item[1] + 1, item[2]))
    for item in res:
        item[2].append(node)
    return res

class CompositeDelegate:

    def __init__(self,edge_id, graph, gopLoader):
        """
         :param gopLoader:
         @type composite: np.ndarry
         @type gopLoader: GroupFilterLoader
        """
        self.gopLoader = gopLoader
        self.edge_id = edge_id
        self.graph = graph
        baseNodeIdsAndLevels = findBaseNodesWithCycleDetection(self.graph, edge_id[0])
        self.baseNodeId, self.level, self.path = baseNodeIdsAndLevels[0] if len(baseNodeIdsAndLevels) > 0 else (None, None)

    def _find_donor_edges(self):
        donors = [(pred, self.edge_id[1]) for pred in self.graph.predecessors(self.edge_id[1])
            if pred != self.edge_id[0] or self.graph.get_edge(pred, self.edge_id[1])['op'] == 'Donor']
        donors.append(self.edge_id)

    def _add_final_node_with_donors(self,
                                    probes,
                                    edge_id,
                                    finalNodeId,
                                    baseNodeId,
                                    target_mask,
                                    target_mask_filename,
                                    level,
                                    donors):

        donormasks = [donor for donor in donors if donor[0] == edge_id[1]]
        if len(donormasks) > 0:
            for image_node, donorbase, donor_mask_image, donor_mask_file_name in donormasks:
                probes.append(Probe(edge_id,
                                    finalNodeId,
                                    baseNodeId,
                                    target_mask,
                                    os.path.join(self.G.dir, target_mask_filename) if target_mask_filename is not None else None,
                                    # ERIC: what to do here
                                    sizeOfChange(np.asarray(target_mask).astype('uint8')),
                                    donorbase,
                                    donor_mask_image,
                                    os.path.join(self.G.dir, donor_mask_file_name),
                                    level=level))
        else:
            probes.append(Probe(edge_id,
                                finalNodeId,
                                baseNodeId,
                                target_mask,
                                os.path.join(self.G.dir, target_mask_filename) if target_mask_filename is not None else None,
                                sizeOfChange(np.asarray(target_mask).astype('uint8')),
                                None,
                                None,
                                None,
                                level=level))

    def constructDonors(self, saveImage=True):
        return []

    def constructComposites(self):
        return self._constructTransformedMask(self.edge_id, self.composite)

    def _constructTransformedMask(self, edge_id, compositeMask):
        return []

    def constructProbes(self,saveTargets=True):
        return []


class ImageCompositeDelegate(CompositeDelegate):

    def __init__(self,edge_id, graph, gopLoader):
        """
        :param edge_id
        :param graph:
        :param gopLoader:
        @type edge_id : (str,str)
        @type graph: ImageGraph
        @type gopLoader: GroupFilterLoader
        """
        CompositeDelegate.__init__(self,edge_id,graph, gopLoader)
        edge = graph.get_edge(edge_id[0], edge_id[1])
        edgeMask = graph.get_edge_image(edge_id[0], edge_id[1], 'maskname')[0]
        self.composite = self.__alterComposite(edge,
                                        gopLoader.getOperationWithGroups(edge['op'], fake=True),
                                        edge_id[0],
                                        edge_id[1],
                                        edgeMask.invert().to_array(),
                                        edgeMask.to_array())




    def constructProbes(self, saveTargets=True):
        selectMasks = _getUnresolvedSelectMasksForEdge(self.graph.get_edge(self.edge_id[0], self.edge_id[1]))
        finaNodeIdMasks = self.__constructTransformedMask(self.edge_id, self.composite)
        probes = []
        for target_mask, finalNodeId in finaNodeIdMasks:
            target_mask = target_mask.invert()
            if finalNodeId in selectMasks:
                try:
                    tm = openImageFile(os.path.join(self.get_dir(), selectMasks[finalNodeId]), isMask=True)
                    target_mask = tm
                except Exception as e:
                    logging.getLogger('maskgen').error('bad replacement file ' + selectMasks[finalNodeId])

            target_mask_filename = os.path.join(self.get_dir(),
                                                    shortenName(self.edge_id[0] + '_' + self.edge_id[1] + '_' + finalNodeId,
                                                                '_ps.png',
                                                                id=self.G.nextId()))
            if saveTargets:
                target_mask.save(target_mask_filename, format='PNG')
            donors = self.constructDonor()
            self._add_final_node_with_donors(probes, self.edge_id, finalNodeId, self.baseNodeId, target_mask,
                                             target_mask_filename, self.level, donors)
        return probes

    def _constructTransformedMask(self, edge_id, compositeMask):
        """
        walks up down the tree from base nodes, assemblying composite masks
        return: list of tuples (transformed mask, final image id)
        @rtype:  list of (ImageWrapper,str))
        """
        results = []
        successors = self.graph.successors(edge_id[1])
        for successor in successors:
            source = edge_id[1]
            target = successor
            edge = self.graph.get_edge(source, target)
            if edge['op'] == 'Donor':
                continue
            edgeMask = self.graph.get_edge_image(source, target, 'maskname', returnNoneOnMissing=True)[0]
            if edgeMask is None:
                raise ValueError('Missing edge mask from ' + source + ' to ' + target)
            edgeMask = edgeMask.to_array()
            newMask = self.__alterComposite(edge,
                                            self.gopLoader.getOperationWithGroups(edge['op'], fake=True),
                                            source,
                                            target,
                                            compositeMask,
                                            edgeMask)
            results.extend(self._constructTransformedMask((source, target), newMask))
        return results if len(successors) > 0 else [(ImageWrapper(np.copy(compositeMask)), edge_id[1])]

    def _saveDonorToFile(self, recipientNode, baseNode, mask):
        """
        Add mask to interim node and save mask to disk that has a input mask or
        a donor link
        """
        if self.graph.has_node(recipientNode):
            fname = shortenName(recipientNode + '_' + baseNode, '_d_mask.png', id=self.G.nextId())
            try:
                mask.save(os.path.abspath(os.path.join(self.get_dir(), fname)))
            except IOError:
                donorMask = convertToMask(mask)
                donorMask.save(os.path.abspath(os.path.join(self.get_dir(), fname)))
        return fname

    def _constructDonor(self, node, mask):
        """
          Walks up  the tree assembling donor masks"
        """
        result = []
        preds = self.G.predecessors(node)
        if len(preds) == 0:
            return [(node, mask)]
        pred_edges = [self.G.get_edge(pred, node) for pred in preds]
        for pred in preds:
            edge = self.G.get_edge(pred, node)
            donorMask = alterDonor(mask,
                                              self.gopLoader.getOperationWithGroups(edge['op'], fake=True),
                                              pred,
                                              node,
                                              edge,
                                              self.G.get_edge_image(pred, node, 'maskname', returnNoneOnMissing=True)[
                                                  0],
                                              directory=self.get_dir(),
                                              pred_edges=[p for p in pred_edges if p != edge],
                                              graph=self.G)
            result.extend(self._constructDonor(pred, donorMask))
        return result

    def constructDonors(self,saveImage = True):

        """
          Construct donor images
          Find all valid base node, leaf node tuples
          :return computed donors in the form of tuples
          (image node id donated to, base image node, ImageWrapper mask, filename)
          @rtype list of (str,str,ImageWapper,str)
        """

        donors = list()
        for edge_id in self._find_donor_edges():
            edge = self.G.get_edge(edge_id[0], edge_id[1])
            startMask = None
            if edge['op'] == 'Donor':
                startMask = self.G.get_edge_image(edge_id[0], edge_id[1], 'maskname', returnNoneOnMissing=True)[0]
                if startMask is None:
                    raise ValueError('Missing donor mask for ' + edge_id[0] + ' to ' + edge_id[1])
            elif 'inputmaskname' in edge and \
                            edge['inputmaskname'] is not None and \
                            len(edge['inputmaskname']) > 0 and \
                            edge['recordMaskInComposite'] == 'yes':
                fullpath = os.path.abspath(os.path.join(self.get_dir(), edge['inputmaskname']))
                if not os.path.exists(fullpath):
                    raise ValueError('Missing input mask for ' + edge_id[0] + ' to ' + edge_id[1])
                    # invert because these masks are white=Keep(unchanged), Black=Remove (changed)
                    # we want to capture the 'unchanged' part, where as the other type we capture the changed part
                startMask = self.G.openImage(fullpath, mask=False).to_mask().invert()
                if startMask is None:
                    raise ValueError('Missing donor mask for ' + edge_id[0] + ' to ' + edge_id[1])
            if startMask is not None:
                startMask = startMask.invert().to_array()
                donorsToNodes = {}
                donor_masks = self._constructDonor(edge_id[0], np.asarray(startMask))
                for donor_mask_tuple in donor_masks:
                    donor_mask = donor_mask_tuple[1].astype('uint8')
                    if sum(sum(donor_mask > 1)) == 0:
                        continue
                    baseNode = donor_mask_tuple[0]
                    if baseNode in donorsToNodes:
                        # same donor image, multiple paths to the image.
                        donorsToNodes[baseNode][donor_mask > 1] = 255
                    else:
                        donorsToNodes[baseNode] = donor_mask.astype('uint8')
                for baseNode, donor_mask in donorsToNodes.iteritems():
                    wrapper = ImageWrapper(donor_mask).invert()
                    if saveImage:
                        fname = self._saveDonorToFile(edge_id[1], baseNode, wrapper)
                    else:
                        fname = None
                    donors.append(baseNode, wrapper, fname)
        return donors

class VideoCompositeDelegate(CompositeDelegate):

    def __init__(self, composite,gopLoader):
        """
               :param composite:
               :param gopLoader:
               @type composite: list()
               @type gopLoader: GroupFilterLoader
        """
        CompositeDelegate.__init__(self, composite, gopLoader)


    def alterComposite(self,edge, op, source, target, edgeMask, directory, level=255, graph=None):
        if op.maskTransformFunction is not None:
            return graph_rules.getRule(op.maskTransformFunction)(edge,
                                                                 source,
                                                                 target,
                                                                 edgeMask,
                                                                 level=level,
                                                                 compositeMask=self.composite,
                                                                 directory=directory,
                                                                 graph=graph)
        return defaultAlterComposite(edge,
                                     edgeMask,
                                     level=level,
                                     compositeMask=self.composite,
                                     directory=directory)


def prepareComposite(edge_id, graph, gopLoader):
    import os
    """
    Depending on the edge properties, construct the composite mask
    :param graph
    :param edge_id: edge
    :param edge:  dictionary of edge
    :return: CompositeDelegate
    @type graph: ImageGraph
    @type edge_id: (str, str)
    @type edge: dict
    """
    edge = graph.get_edge(edge_id[0], edge_id[1])
    if 'videomasks' in edge:
        return VideoCompositeDelegate(edge['videomasks'])
    return ImageCompositeDelegate(edge_id, graph, gopLoader)

