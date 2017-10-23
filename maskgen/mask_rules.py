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
from maskgen import Probe, VideoSegment
import video_tools
from collections import namedtuple

DonorImage = namedtuple('DonorImage', ['target', 'base', 'mask_wrapper', 'mask_file_name', 'media_type'], verbose=True)
CompositeImage = namedtuple('CompositeImage', ['source', 'target', 'media_type', 'videomasks'])


def _compositeImageToVideoSegment(compositeImage):
    """

    :param compositeImage:
    :return:
    @type compositeImage: CompositeImage
    """
    return [VideoSegment(item['rate'],
                         item['starttime'],
                         item['startframe'],
                         item['endtime'],
                         item['endframe'],
                         item['frames'],
                         item['videosegment'] if 'videosegment' in item else None,
                         item['type']) for item in compositeImage.videomasks]


def _is_empty_composite(composite):
    if (type(composite) == CompositeImage and len(composite.videomasks) == 0) or \
        composite is None:
        return True
    return False


def _guess_type(edge):
    """

    :param edge:
    :return:
    @type edge: dict
    """
    return 'audio' if edge['op'].find('Audio') >= 0 else 'video'


def _prepare_video_masks(directory, video_masks, media_type, source, target, returnEmpty=True):
    """
    Remove empty videosegments, set the videosegment file names to full path names,
    set the media_type of the segment if missing.
    :param directory:
    :param video_masks:
    :param media_type:
    :param source:
    :param target:
    :param returnEmpty: If True, emoty masks (e.g. []) is permitted, otherwise return None
    :return: CompositeImage
    @rtype: CompositeImage
    """
    import copy
    def replace_with_dir(directory, video_masks):
        for mask in video_masks:
            mask_copy = copy.deepcopy(mask)
            if 'type' not in mask_copy:
                mask_copy['type'] = media_type
            if 'videosegment' in mask:
                if mask['videosegment'] is None:
                    mask_copy.pop('videosegment')
                else:
                    mask_copy['videosegment'] = os.path.join(directory, os.path.split(mask_copy['videosegment'])[1])
                    if not os.path.exists(mask_copy['videosegment']):
                        mask_copy.pop('videosegment')
            yield mask_copy

    return None if len(video_masks) == 0 and not returnEmpty else \
         CompositeImage(source, target, media_type, [item for item in replace_with_dir(directory, video_masks)])


def recapture_transform(edge, source, target, edgeMask,
                        compositeMask=None,
                        directory='.',
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


def video_resize_transform(edge,
                           source,
                           target,
                           edgeMask,
                           compositeMask=None,
                           directory='.',
                           donorMask=None,
                           pred_edges=None,
                           graph=None):
    sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
    args = edge['arguments'] if 'arguments' in edge else {}
    canvas_change = (sizeChange != (0, 0) and 'interpolation' in args and 'none' == args['interpolation'].lower())
    if compositeMask is not None:
        expectedSize = getNodeSize(graph, target)
        if canvas_change:
            return CompositeImage(compositeMask.source,
                                  compositeMask.target,
                                  compositeMask.media_type,
                                  video_tools.resizeMask(compositeMask.videomasks, expectedSize))
        return compositeMask
    elif donorMask is not None:
        expectedSize = getNodeSize(graph, source)
        if canvas_change:
            return CompositeImage(donorMask.source,
                                  donorMask.target,
                                  donorMask.media_type,
                                  video_tools.resizeMask(donorMask.videomasks, expectedSize))
        return donorMask
    return None


def rotate_transform(edge, source, target, edgeMask,
                     compositeMask=None,
                     directory='.',
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
    res = None
    if donorMask is not None:
        if tm is not None:
            res = tool_set.applyTransform(donorMask, mask=edgeMask, transform_matrix=tool_set.deserializeMatrix(tm),
                                          invert=True,
                                          returnRaw=False)
        else:
            targetSize = edgeMask.shape if edgeMask is not None else (0, 0)
            res = tool_set.__rotateImage(-rotation, donorMask, expectedDims=targetSize, cval=0)
    elif compositeMask is not None:
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


def video_rotate_transform(edge, source, target, edgeMask,
                           compositeMask=None,
                           directory='.',
                           donorMask=None,
                           pred_edges=None,
                           graph=None):
    args = edge['arguments'] if 'arguments' in edge else {}
    rotation = float(args['rotation'] if 'rotation' in args and args['rotation'] is not None else 0)
    rotation = rotation if rotation is not None and abs(rotation) > 0.00001 else 0
    if compositeMask is not None:
        targetSize = getNodeSize(graph, target)
        return video_tools.rotateMask(rotation, compositeMask, expectedDims=targetSize, cval=0)
    elif donorMask is not None:
        targetSize = getNodeSize(graph, source)
        return video_tools.rotateMask(-rotation, donorMask, expectedDims=targetSize, cval=0)
    return None


def select_cut_frames(edge, source, target, edgeMask,
                      compositeMask=None,
                      directory='.',
                      donorMask=None,
                      pred_edges=None,
                      graph=None):
    start, end = video_tools.getStartAndEndTimesFromEdge(edge)
    if compositeMask is not None:
        return CompositeImage(compositeMask.source,
                              compositeMask.target,
                              compositeMask.media_type,
                              video_tools.dropFramesFromMask(start, end, compositeMask.videomasks))
    elif donorMask is not None:
        return CompositeImage(donorMask.source,
                              donorMask.target,
                              donorMask.media_type,
                              video_tools.insertFramesToMask(start, end, donorMask.videomasks))
    return None


def select_crop_frames(edge, source, target, edgeMask,
                       compositeMask=None,
                       directory='.',
                       donorMask=None,
                       pred_edges=None,
                       graph=None):
    start, end = video_tools.getStartAndEndTimesFromEdge(edge)
    if compositeMask is not None:
        return CompositeImage(compositeMask.source,
                              compositeMask.target,
                              compositeMask.media_type,
                              video_tools.dropFramesFromMask(end, None,
                                                             video_tools.dropFramesFromMask('00:00:00.000', start,
                                                                                            compositeMask.videomasks)))
    elif donorMask is not None:
        return CompositeImage(donorMask.source,
                              donorMask.target,
                              donorMask.media_type,
                              video_tools.insertFramesToMask('00:00:00.000', start, donorMask.videomasks))
    return None


def replace_audio(edge, source, target, edgeMask,
                  compositeMask=None,
                  directory='.',
                  donorMask=None,
                  pred_edges=None,
                  graph=None):
    args = edge['arguments'] if 'arguments' in edge else {}
    start, end = video_tools.getStartAndEndTimesFromEdge(edge)  # overlay case, trim masks
    if compositeMask is not None:
        return CompositeImage(compositeMask.source,
                              compositeMask.target,
                              compositeMask.media_type,
                              video_tools.dropFramesWithoutMask(start, end, compositeMask.videomasks, keepTime=True,
                                                                expectedType='audio'))
    # in donor case, the donor was already trimmed
    else:
        return donorMask


def add_audio(edge, source, target, edgeMask,
              compositeMask=None,
              directory='.',
              donorMask=None,
              pred_edges=None,
              graph=None):
    args = edge['arguments'] if 'arguments' in edge else {}
    start, end = video_tools.getStartAndEndTimesFromEdge(edge)  # overlay case, trim masks
    if compositeMask is not None:
        # if there is a match the source and target, then this is 'seeded' composite mask
        # have to wonder if this is necessary, but I suppose it gives the transform
        # an opportunity to make adjustments for composite.
        if compositeMask.source != source and compositeMask.target != target:
            return CompositeImage(compositeMask.source,
                                  compositeMask.target,
                                  compositeMask.media_type,
                                  video_tools.dropFramesWithoutMask(start, end, compositeMask.videomasks, keepTime=True,
                                                                    expectedType='audio'))
        return compositeMask
    # in donor case, the donor was already trimmed
    else:
        return donorMask


def delete_audio(edge, source, target, edgeMask,
                 compositeMask=None,
                 directory='.',
                 donorMask=None,
                 pred_edges=None,
                 graph=None):
    start, end = video_tools.getStartAndEndTimesFromEdge(edge)  # overlay case, trim masks
    if compositeMask is not None:
        if compositeMask.source != source and compositeMask.target != target:
            return CompositeImage(compositeMask.source,
                                  compositeMask.target,
                                  compositeMask.media_type,
                                  video_tools.dropFramesWithoutMask(start, end, compositeMask.videomasks,
                                                                    expectedType='audio'))
        return compositeMask
    # in donor case, need to add the deleted frames back
    else:
        return video_tools.insertFramesWithoutMask(start, end, compositeMask, expectedType='audio')


def paste_add_frames(edge, source, target, edgeMask,
                     compositeMask=None,
                     directory='.',
                     donorMask=None,
                     pred_edges=None,
                     graph=None):
    args = edge['arguments'] if 'arguments' in edge else {}
    start, end = video_tools.getStartAndEndTimesFromEdge(edge)
    if 'add type' in args and args['add type'] == 'insert':
        if compositeMask is not None:
            if compositeMask.source != source and compositeMask.target != target:
                return CompositeImage(compositeMask.source,
                                      compositeMask.target,
                                      compositeMask.media_type,
                                      video_tools.insertFramesToMask(start, end, compositeMask.videomasks))
            return compositeMask
        elif donorMask is not None:
            return CompositeImage(donorMask.source,
                                  donorMask.target,
                                  donorMask.media_type,
                                  video_tools.dropFramesFromMask(start, end, donorMask.videomasks))
        return None
    else:
        # overlay case, trim masks
        if compositeMask is not None:
            if compositeMask.source != source and compositeMask.target != target:
                return CompositeImage(compositeMask.source,
                                      compositeMask.target,
                                      compositeMask.media_type,
                                      video_tools.dropFramesFromMask(start, end, compositeMask.videomasks,
                                                                     keepTime=True))
            return compositeMask
        # in donor case, the donor was already trimmed
        else:
            return donorMask


# ERIC
def paste_add_audio_frames(edge, source, target, edgeMask,
                           compositeMask=None,
                           directory='.',
                           donorMask=None,
                           pred_edges=None,
                           graph=None):
    args = edge['arguments'] if 'arguments' in edge else {}
    start, end = video_tools.getStartAndEndTimesFromEdge(edge)
    if 'add type' in args and args['add type'] == 'insert':
        if compositeMask is not None:
            if compositeMask.source != source and compositeMask.target != target:
                return CompositeImage(compositeMask.source,
                                      compositeMask.target,
                                      compositeMask.media_type,
                                      video_tools.insertFramesToMask(start, end, compositeMask.videomasks))
            return compositeMask
        elif donorMask is not None:
            return CompositeImage(donorMask.source,
                                  donorMask.target,
                                  donorMask.media_type,
                                  video_tools.dropFramesFromMask(start, end, donorMask.videomasks))
        return None
    else:
        # overlay case, trim masks
        if compositeMask is not None:
            if compositeMask.source != source and compositeMask.target != target:
                return CompositeImage(compositeMask.source,
                                      compositeMask.target,
                                      compositeMask.media_type,
                                      video_tools.dropFramesFromMask(start, end, compositeMask.videomasks,
                                                                     keepTime=True))
            return compositeMask
        # in donor case, the donor was already trimmed
        else:
            return donorMask


def select_remove(edge, source, target, edgeMask,
                  compositeMask=None,
                  directory='.',
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
        if res is not None and targetSize != res.shape:
            res = cv2.resize(res, (targetSize[1], targetSize[0]))
        return res


def crop_transform(edge, source, target, edgeMask,
                   compositeMask=None,
                   directory='.',
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


def video_crop_transform(edge, source, target, edgeMask,
                         compositeMask=None,
                         directory='.',
                         donorMask=None,
                         pred_edges=None,
                         graph=None):
    targetSize = getNodeSize(graph, target)
    sourceSize = getNodeSize(graph, source)
    sizeChange = (sourceSize[0] - targetSize[0], sourceSize[1] - targetSize[1])
    location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0, 0)
    if compositeMask is not None:
        expectedSize = targetSize
        return CompositeImage(compositeMask.source,
                              compositeMask.target,
                              compositeMask.media_type,
                              video_tools.cropMask(compositeMask.videomasks,
                                                   (location(0), location[1], expectedSize[0], expectedSize[1])))
    elif donorMask is not None:
        expectedSize = sourceSize
        upperBound = (min(targetSize[0],sourceSize[0] + location[0]),
                      min(targetSize[1], sourceSize[0] + location[1]))
        return CompositeImage(donorMask.source,
                              donorMask.target,
                              donorMask.media_type,
                              video_tools.insertMask(
                                  donorMask.videomasks,
                                  (location[0], location[1], upperBound[0], upperBound[1]),
                                  expectedSize))
    return None


def seam_transform(edge,
                   source,
                   target,
                   edgeMask,
                   compositeMask=None,
                   directory='.',
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
        elif donorMask is not None:
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

    elif donorMask is not None or compositeMask is not None:
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
                                    donorMask=donorMask,
                                    pred_edges=pred_edges,
                                    graph=graph)
    return res


def video_flip_transform(edge,
                         source,
                         target,
                         edgeMask,
                         compositeMask=None,
                         directory='.',
                         donorMask=None,
                         pred_edges=None,
                         graph=None):
    args = edge['arguments'] if 'arguments' in edge else {}
    flip = args['flip direction'] if 'flip direction' in args else None
    if compositeMask is not None:
        expectedSize = getNodeSize(graph, target)
        return CompositeImage(compositeMask.source,
                              compositeMask.target,
                              compositeMask.media_type,
                              video_tools.flipMask(compositeMask.videomasks, expectedSize, flip))
    elif donorMask is not None:
        expectedSize = getNodeSize(graph, source)
        return CompositeImage(donorMask.source,
                              donorMask.target,
                              donorMask.media_type,
                              video_tools.flipMask(donorMask.videomasks, expectedSize, flip))
    return donorMask


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
                donorMask=None,
                pred_edges=None,
                graph=None):
    import os
    if compositeMask is not None:
        return compositeMask
    elif donorMask is not None:
        # during a paste splice, the edge mask can split up the donor.
        # although I am wondeing if the edgemask needs to be inverted.
        # this effectively sets the donorMask pixels to 0 where the edge mask is 0 (which is 'changed')
        donorMask = tool_set.applyMask(donorMask, edgeMask)
    return donorMask


def select_region_frames(edge, source, target,
                         edgeMask,
                         compositeMask=None,
                         directory='.',
                         donorMask=None,
                         pred_edges=None,
                         graph=None):
    if compositeMask is not None:
        return compositeMask
    elif donorMask is not None:
        return donorMask
    return _prepare_video_masks(directory, edge['videomasks'], 'video', source,
                                target) if 'videomasks' in edge else None


def select_region(edge, source, target,
                  edgeMask,
                  compositeMask=None,
                  directory='.',
                  donorMask=None,
                  pred_edges=None,
                  graph=None):
    if compositeMask is not None:
        return compositeMask
    elif donorMask is not None:
        return donorMask
    return edgeMask


def getNodeSize(graph, nodeid):
    node = graph.get_node(nodeid)
    if node is not None and 'shape' in node:
        return (node['shape'][0],node['shape'][1])
    else:
        return video_tools.getShape(graph.get_image_path(nodeid))


def getNodeFileType(graph, nodeid):
    node = graph.get_node(nodeid)
    if node is not None and 'filetype' in node:
        return node['filetype']
    else:
        return tool_set.fileType(graph.get_image_path(nodeid))


def donor(edge, source, target, edgeMask,
          compositeMask=None,
          directory='.',
          donorMask=None,
          pred_edges=None,
          graph=None,
          top=False
          ):
    if compositeMask is not None:
        return compositeMask
    elif donorMask is not None:
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


def image_to_video(edge, source, target, edgeMask,
                   compositeMask=None,
                   directory='.',
                   donorMask=None,
                   pred_edges=None,
                   graph=None,
                   top=False
                   ):
    if compositeMask is not None:
        return _prepare_video_masks(directory,
                                    video_tools.getMaskSetForEntireVideo(graph.get_image_path(target)),
                                    'video',
                                    source,
                                    target)
    else:
        wrapper, name = graph.get_image(source)
        return np.ones(wrapper.to_array().size, dtype=np.uint8) * 255


def video_donor(edge, source, target, edgeMask,
                compositeMask=None,
                directory='.',
                donorMask=None,
                pred_edges=None,
                graph=None,
                top=False
                ):
    if compositeMask is not None:
        return compositeMask
    else:
        return _prepare_video_masks(directory, edge['videomasks'], 'video', source, target) if donorMask is None and \
                                                                                               'videomasks' in edge and \
                                                                                               len(edge[
                                                                                                       'videomasks']) > 0 else donorMask


def audio_donor(edge, source, target, edgeMask,
                compositeMask=None,
                directory='.',
                donorMask=None,
                pred_edges=None,
                graph=None,
                top=False
                ):
    if compositeMask is not None:
        return compositeMask
    else:
        node = graph.get_node(target)
        if getNodeFileType(graph, node) in ['video', 'audio']:
            return _prepare_video_masks(directory, edge['videomasks'], 'audio',
                                        source, target) if donorMask is None and \
                                                           'videomasks' in edge and \
                                                           len(edge['videomasks']) > 0 else donorMask
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


def defaultAlterComposite(edge, edgeMask, compositeMask=None):
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


def defaultAlterDonor(edge, edgeMask, donorMask=None):
    if donorMask is None:
        return donorMask
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


def _getMaskTranformationFunction(
        op,
        source,
        target,
        graph=None):
    sourceType = getNodeFileType(graph, source)
    if op.maskTransformFunction is not None and sourceType in op.maskTransformFunction:
        return graph_rules.getRule(op.maskTransformFunction[sourceType])
    return None


def defaultMaskTransform(edge,
                         source,
                         target,
                         edgeMask,
                         compositeMask=None,
                         directory='.',
                         donorMask=None,
                         pred_edges=None,
                         graph=None):
    if compositeMask is not None:
        return defaultAlterComposite(edge, edgeMask,
                                     compositeMask=compositeMask)
    else:
        return defaultAlterDonor(edge, edgeMask, donorMask=donorMask)


def alterDonor(donorMask, op, source, target, edge, directory='.', pred_edges=[], graph=None):
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

    transformFunction = _getMaskTranformationFunction(op, source, target, graph=graph)

    edgeMask = graph.get_edge_image(source, target, 'maskname', returnNoneOnMissing=True)[0]

    if 'videomasks' in edge or 'Start Time' in edge:
        if transformFunction is not None:
            return transformFunction(edge,
                                     source,
                                     target,
                                     np.toarray(edgeMask) if edgeMask is not None else None,
                                     donorMask=donorMask if len(donorMask) > 0 else None,
                                     directory=directory,
                                     pred_edges=pred_edges,
                                     graph=graph)
        return donorMask

    if edgeMask is None:
        raise ValueError('Missing edge mask from ' + source + ' to ' + target)
    edgeMask = edgeMask.to_array()
    if transformFunction is not None:
        return transformFunction(edge,
                                 source,
                                 target,
                                 edgeMask,
                                 directory=directory,
                                 donorMask=donorMask,
                                 pred_edges=pred_edges,
                                 graph=graph)

    return defaultAlterDonor(edge, edgeMask, donorMask=donorMask)


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
        for item in findBaseNodesWithCycleDetection(graph, pred, excludeDonor=excludeDonor):
            res.append((item[0], item[1] + 1, item[2]))
    for item in res:
        item[2].append(node)
    return res


def alterComposite(graph,
                   edge,
                   op,
                   source,
                   target,
                   composite,
                   directory,
                   replacementEdgeMask=None):
    """

    :param graph:
    :param edge:
    :param op:
    :param source:
    :param target:
    :param composite:
    :param directory:
    :param replacementEdgeMask:
    :return:
    @type composite: np.ndarray
    """
    edgeMask = graph.get_edge_image(source, target, 'maskname', returnNoneOnMissing=True)[
        0] if replacementEdgeMask is None else ImageWrapper(replacementEdgeMask)
    transformFunction = _getMaskTranformationFunction(op, source, target, graph=graph)

    if 'videomasks' in edge or 'Start Time' in edge:
        compositeMask = _prepare_video_masks(directory, edge['videomasks'], _guess_type(edge),
                                             source, target) if composite is None else composite
        if transformFunction is not None:
            return transformFunction(edge,
                                     source,
                                     target,
                                     np.asarray(edgeMask) if edgeMask is not None else None,
                                     compositeMask=compositeMask,
                                     directory=directory,
                                     graph=graph)
        return compositeMask

    if edgeMask is None:
        raise ValueError('Missing edge mask from ' + source + ' to ' + target)
    compositeMask = edgeMask.invert().to_array() if composite is None else composite
    edgeMask = edgeMask.to_array()
    if transformFunction is not None:
        return transformFunction(edge,
                                 source,
                                 target,
                                 edgeMask,
                                 compositeMask=compositeMask,
                                 directory=directory,
                                 graph=graph)
    return defaultAlterComposite(edge,
                                 edgeMask,
                                 compositeMask=compositeMask)


class CompositeDelegate:
    composite = None

    def __init__(self, edge_id, graph, gopLoader):
        """
        :param edge_id
        :param graph:
        :param gopLoader:
        @type edge_id : (str,str)
        @type graph: ImageGraph
        @type gopLoader: GroupFilterLoader
        """
        self.gopLoader = gopLoader
        self.edge_id = edge_id
        self.graph = graph
        baseNodeIdsAndLevels = findBaseNodesWithCycleDetection(self.graph, edge_id[0])
        self.baseNodeId, self.level, self.path = baseNodeIdsAndLevels[0] if len(baseNodeIdsAndLevels) > 0 else (
        None, None)

    def _getComposite(self):
        if self.composite is not None:
            return self.composite
        edge = self.graph.get_edge(self.edge_id[0], self.edge_id[1])
        self.composite = alterComposite(self.graph,
                                        edge,
                                        self.gopLoader.getOperationWithGroups(edge['op'], fake=True),
                                        self.edge_id[0],
                                        self.edge_id[1],
                                        None,
                                        self.get_dir())
        return self.composite

    def find_donor_edges(self):
        donors = [(pred, self.edge_id[1]) for pred in self.graph.predecessors(self.edge_id[1])
                  if pred != self.edge_id[0] or self.graph.get_edge(pred, self.edge_id[1])['op'] == 'Donor']
        donors.append(self.edge_id)
        return donors

    def constructComposites(self):
        return self.constructTransformedMask(self.edge_id, self._getComposite())

    def get_dir(self):
        return self.graph.dir

    def constructTransformedMask(self, edge_id, compositeMask, saveTargets=False):
        """
        walks up down the tree from base nodes, assemblying composite masks
        return: list of tuples (transformed mask, final image id)
        @rtype:  list of (ImageWrapper(compositeMask),str))
        """
        results = []
        successors = self.graph.successors(edge_id[1])
        for successor in successors:
            source = edge_id[1]
            target = successor
            edge = self.graph.get_edge(source, target)
            if edge['op'] == 'Donor':
                continue
            newMask = alterComposite(self.graph,
                                     edge,
                                     self.gopLoader.getOperationWithGroups(edge['op'], fake=True),
                                     source,
                                     target,
                                     compositeMask,
                                     self.get_dir())
            results.extend(self.constructTransformedMask((source, target), newMask, saveTargets=saveTargets))
        return results if len(successors) > 0 else [
            self._finalizeCompositeMask(compositeMask, edge_id[1], saveTargets=saveTargets)]

    def constructProbes(self, saveTargets=True):
        """

        :param saveTargets:
        :return:
        %rtype: list of Probe
        """
        selectMasks = _getUnresolvedSelectMasksForEdge(self.graph.get_edge(self.edge_id[0], self.edge_id[1]))
        finaNodeIdMasks = self.constructTransformedMask(self.edge_id, self._getComposite(), saveTargets=saveTargets)
        probes = []
        for target_mask, target_mask_filename, finalNodeId, nodetype in finaNodeIdMasks:
            if finalNodeId in selectMasks:
                try:
                    tm = openImageFile(os.path.join(self.get_dir(),
                                                    selectMasks[finalNodeId]),
                                       isMask=True)
                    target_mask = tm
                    if saveTargets and target_mask_filename is not None:
                        target_mask.save(target_mask_filename, format='PNG')
                except Exception as e:
                    logging.getLogger('maskgen').error('bad replacement file ' + selectMasks[finalNodeId])
            donors = self.constructDonors(saveImage=saveTargets)
            self.___add_final_node_with_donors(probes,
                                               self.edge_id,
                                               finalNodeId,
                                               self.baseNodeId,
                                               target_mask,
                                               target_mask_filename,
                                               self.level,
                                               nodetype,
                                               donors)
        return probes

    def _finalizeCompositeMask(self, mask, finalNodeId, saveTargets=False):
        """
        :param mask:
        :param finalNodeId:
        :return:  mask, file name and final node id
        """
        if type(mask) == np.ndarray:
            target_mask_filename = os.path.join(self.get_dir(),
                                                shortenName(self.edge_id[0] + '_' + self.edge_id[1] + '_' + finalNodeId,
                                                            '_ps.png',
                                                            id=self.graph.nextId()))
            target_mask = ImageWrapper(mask).invert()
            if saveTargets:
                target_mask.save(target_mask_filename, format='PNG')
            return target_mask, target_mask_filename, finalNodeId, 'image'

        return mask, None, finalNodeId, 'video'

    def ___add_final_node_with_donors(self,
                                      probes,
                                      edge_id,
                                      finalNodeId,
                                      baseNodeId,
                                      target_mask,
                                      target_mask_filename,
                                      level,
                                      nodetype,
                                      donors):
        """

        :param probes:
        :param edge_id:
        :param finalNodeId:
        :param baseNodeId:
        :param target_mask:
        :param target_mask_filename:
        :param level:
        :param nodetype:
        :param donors:
        :return:
        @type donors : list(DonorImage)
        """
        donormasks = [donor for donor in donors if donor[0] == edge_id[1]]
        if len(donormasks) > 0:
            for donortuple in donormasks:
                probes.append(Probe(edge_id,
                                    finalNodeId,
                                    baseNodeId,
                                    donortuple.base,
                                    targetMaskImage=target_mask if nodetype == 'image' else tool_set.getSingleFrameFromMask(
                                        target_mask.videomasks),
                                    targetMaskFileName=target_mask_filename if target_mask_filename is not None else None,
                                    targetVideoSegments=_compositeImageToVideoSegment(
                                        target_mask) if nodetype != 'image' else None,
                                    # TODO: what to do here
                                    targetChangeSizeInPixels=sizeOfChange(
                                        np.asarray(target_mask).astype('uint8')) if nodetype == 'image' else None,
                                    donorMaskImage=donortuple.mask_wrapper if donortuple.media_type == 'image' else tool_set.getSingleFrameFromMask(
                                        donortuple.mask_wrapper.videomasks),
                                    donorMaskFileName=donortuple.mask_file_name if donortuple.media_type == 'image' else None,
                                    donorVideoSegments=_compositeImageToVideoSegment(
                                        donortuple.mask_wrapper) if donortuple.media_type != 'image' else None,
                                    level=level))
        else:
            probes.append(Probe(edge_id,
                                finalNodeId,
                                baseNodeId,
                                None,
                                targetMaskImage=target_mask if nodetype == 'image' else tool_set.getSingleFrameFromMask(
                                    target_mask.videomasks),
                                targetMaskFileName=target_mask_filename if target_mask_filename is not None else None,
                                targetVideoSegments=_compositeImageToVideoSegment(
                                    target_mask) if nodetype != 'image' else None,
                                # TODO: what to do here
                                targetChangeSizeInPixels=sizeOfChange(
                                    np.asarray(target_mask).astype('uint8')) if nodetype == 'image' else None,
                                level=level))

    def _constructDonor(self, node, mask):
        """
        Walks up the tree assembling donor masks
        """
        result = []
        preds = self.graph.predecessors(node)
        if len(preds) == 0:
            return [(node, mask)]
        pred_edges = [self.graph.get_edge(pred, node) for pred in preds]
        for pred in preds:
            edge = self.graph.get_edge(pred, node)
            donorMask = alterDonor(mask,
                                   self.gopLoader.getOperationWithGroups(edge['op'], fake=True),
                                   pred,
                                   node,
                                   edge,
                                   directory=self.get_dir(),
                                   pred_edges=[p for p in pred_edges if p != edge],
                                   graph=self.graph)
            result.extend(self._constructDonor(pred, donorMask))
        return result

    def __getDonorMaskForEdge(self, edge_id):
        edge = self.graph.get_edge(edge_id[0], edge_id[1])
        if 'videomasks' in edge:
            return _prepare_video_masks(self.graph.dir, edge['videomasks'], _guess_type(edge), edge_id[0], edge_id[1])
        startMask = self.graph.get_edge_image(edge_id[0], edge_id[1], 'maskname', returnNoneOnMissing=True)[0]
        if startMask is None:
            raise ValueError('Missing donor mask for ' + edge_id[0] + ' to ' + edge_id[1])
        return startMask.invert().to_array()

    def __processImageDonor(self, donor_masks):
        """
        merge donors that are aligned to the same base node (through multiple paths)
        :param donor_masks:  a tuple of base node name and donor mask
        :return:
        """
        imageDonorToNodes = {}
        for donor_mask_tuple in donor_masks:
            if type(donor_mask_tuple[1]) != np.ndarray:
                continue
            donor_mask = donor_mask_tuple[1].astype('uint8')
            if sum(sum(donor_mask > 1)) == 0:
                continue
            baseNode = donor_mask_tuple[0]
            if baseNode in imageDonorToNodes:
                # same donor image, multiple paths to the image.
                imageDonorToNodes[baseNode][donor_mask > 1] = 255
            else:
                imageDonorToNodes[baseNode] = donor_mask.astype('uint8')
        return imageDonorToNodes

    def __mergeVideoDonorMasks(self, mask1, mask2):
        """
        merge donors that are aligned to the same base node (through multiple paths)
        Merge to video masks
        TODO
        :param mask1:
        :param mask2:
        :return:
        """
        return mask1

    def __processVideoDonor(self, donor_masks):
        """
         merge donors that are aligned to the same base node (through multiple paths)
         :param donor_masks:  a tuple of base node name and donor mask
         :return:
        """
        videoDonorToNodes = {}
        for donor_mask_tuple in donor_masks:
            if type(donor_mask_tuple[1]) == np.ndarray:
                continue
            baseNode = donor_mask_tuple[0]
            if baseNode in videoDonorToNodes:
                # same donor image, multiple paths to the image.
                videoDonorToNodes[baseNode] = self.__mergeVideoDonorMasks(videoDonorToNodes[baseNode],
                                                                          donor_mask_tuple[1])
            else:
                videoDonorToNodes[baseNode] = donor_mask_tuple[1]
        return videoDonorToNodes

    def __saveDonorImageToFile(self, recipientNode, baseNode, mask):
        if self.graph.has_node(recipientNode):
            fname = shortenName(recipientNode + '_' + baseNode, '_d_mask.png', id=self.graph.nextId())
            fname = os.path.abspath(os.path.join(self.get_dir(), fname))
            try:
                mask.save(fname)
            except IOError:
                donorMask = convertToMask(mask)
                donorMask.save(fname)
        return fname

    def __saveDonorVideoToFile(self, recipientNode, baseNode, mask):
        return None

    def __imagePreprocess(self, mask):
        return ImageWrapper(mask).invert()

    def __videoPreprocess(self, mask):
        return mask

    def __doNothingSave(self, recipientNode, baseNode, mask):
        return None

    def __saveDonors(self, target, nodeToDonorDictionary, preprocessFunction, saveFunction, media_type):
        donors = list()
        for baseNode, donor_mask in nodeToDonorDictionary.iteritems():
            mask_wrapper = preprocessFunction(donor_mask)
            fname = saveFunction(target, baseNode, mask_wrapper)
            donors.append(DonorImage(target, baseNode, mask_wrapper, fname, media_type))
        return donors

    def constructDonors(self, saveImage=True):
        """
          Construct donor images
          Find all valid base node, leaf node tuples
          :return computed donors in the form of tuples
          (image node id donated to, base image node, ImageWrapper mask, filename)
          @rtype list of DonorImage
        """
        donors = list()
        for edge_id in self.find_donor_edges():
            edge = self.graph.get_edge(edge_id[0], edge_id[1])
            startMask = None
            if edge['op'] == 'Donor':
                startMask = self.__getDonorMaskForEdge(edge_id)
            elif 'inputmaskname' in edge and \
                            edge['inputmaskname'] is not None and \
                            len(edge['inputmaskname']) > 0 and \
                            edge['recordMaskInComposite'] == 'yes':
                fullpath = os.path.abspath(os.path.join(self.get_dir(), edge['inputmaskname']))
                if not os.path.exists(fullpath):
                    raise ValueError('Missing input mask for ' + edge_id[0] + ' to ' + edge_id[1])
                    # we do need to invert because these masks are white=Keep(unchanged), Black=Remove (changed)
                    # we want to capture the 'unchanged' part, where as the other type we capture the changed part
                startMask = self.graph.openImage(fullpath, mask=False).to_mask().to_array()
                if startMask is None:
                    raise ValueError('Missing donor mask for ' + edge_id[0] + ' to ' + edge_id[1])
            if startMask is not None:
                if _is_empty_composite(startMask):
                    startMask = None
                donor_masks = self._constructDonor(edge_id[0], startMask)
                imageDonorToNodes = self.__processImageDonor(donor_masks)
                videoDonorToNodes = self.__processVideoDonor(donor_masks)
                donors.extend(self.__saveDonors(edge_id[1], imageDonorToNodes, self.__imagePreprocess,
                                                self.__saveDonorImageToFile if saveImage else self.__saveDonorImageToFile,
                                                'image'))
                donors.extend(self.__saveDonors(edge_id[1], videoDonorToNodes, self.__videoPreprocess,
                                                self.__saveDonorVideoToFile if saveImage else self.__doNothingSave,
                                                'video'))
        return donors


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
    return CompositeDelegate(edge_id, graph, gopLoader)
