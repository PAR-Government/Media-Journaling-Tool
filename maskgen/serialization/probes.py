# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from maskgen.mask_rules import Probe, VideoSegment
import os
import shutil
from maskgen.tool_set import openImage


def serialize_segment(segment, copyFileDirectory=None):
    """
    :param segment:
    :return:
    @type segment: VideoSegment
    """
    if copyFileDirectory is not None:
        shutil.copy(segment.filename,
                    os.path.join(copyFileDirectory, os.path.basename(segment.filename)))
    return {"startframe": segment.startframe,
            "starttime": segment.starttime,
            "endframe": segment.endframe,
            "endtime": segment.endtime,
            "frames": segment.frames,
            "rate": segment.rate,
            "type": segment.media_type,
            "error":segment.error}


def serialize_probe(probe, copyFileDirectory=None):
    """

    :param probe:
    :return:
    @type probe: Probe
    """
    item = {}
    item['targetBaseNodeId'] = probe.targetBaseNodeId
    item['edgeId'] = probe.edgeId
    item['finalNodeId'] = probe.finalNodeId
    item['donorBaseNodeId'] = probe.donorBaseNodeId
    if probe.targetMaskFileName is not None:
        item['targetMaskFileName'] = os.path.basename(probe.targetMaskFileName)
        if copyFileDirectory is not None:
            shutil.copy(probe.targetMaskFileName,
                        os.path.join(copyFileDirectory, os.path.basename(probe.targetMaskFileName)))
    if probe.donorMaskFileName is not None:
        if copyFileDirectory is not None:
            shutil.copy(probe.donorMaskFileName,
                        os.path.join(copyFileDirectory, os.path.basename(probe.donorMaskFileName)))
        item['donorMaskFileName'] = os.path.basename(probe.donorMaskFileName)
    targetsegment = []
    donorsegment = []
    if probe.targetVideoSegments is not None:
        for segment in probe.targetVideoSegments:
            targetsegment.append(serialize_segment(segment))
    if probe.donorVideoSegments is not None:
        for segment in probe.donorVideoSegments:
            donorsegment.append(serialize_segment(segment))
    item['targetsegments'] = targetsegment
    item['donorsegments'] = donorsegment
    return item


def deserialize_segment(segmentItem, fileDirectory='.'):
    return VideoSegment(segmentItem["rate"],
                        segmentItem["starttime"],
                        segmentItem["startframe"],
                        segmentItem["endtime"],
                        segmentItem["endframe"],
                        segmentItem["frames"],
                        os.path.join(fileDirectory, segmentItem["filename"]) if "filename" in segmentItem else None,
                        segmentItem["type"],
                        0)


def deserialize_probe(probeItem, fileDirectory='.'):
    """
    :param probeItem: dict[str,str]
    :return:
    @rtype Probe
    """
    from maskgen.tool_set import getValue

    def deserializeSegments(segments, fileDirectory='.'):
        return [deserialize_segment(item, fileDirectory=fileDirectory) for item in segments]

    def resolveFile(item, key, fileDirectory):
        if key in item:
            return os.path.join(fileDirectory, item[key]) if fileDirectory is not None else item[key]
        return None

    return Probe(probeItem['edgeId'],
                 probeItem['finalNodeId'],
                 probeItem['targetBaseNodeId'],
                 probeItem['donorBaseNodeId'],
                 donorMaskFileName=resolveFile(probeItem, 'donorMaskFileName', fileDirectory),
                 targetMaskFileName=resolveFile(probeItem, 'targetMaskFileName', fileDirectory),
                 targetVideoSegments=deserializeSegments(getValue(probeItem,'targetsegments',[]), fileDirectory=fileDirectory),
                 donorVideoSegments=deserializeSegments(getValue(probeItem,'donorsegments',[]), fileDirectory=fileDirectory)
                 )


def compare_mask_images(got, expected):
    """

    :param got:
    :param expected:
    :return:
    @type got: ImageWrapper
    @type expected: ImageWrapper
    """
    import numpy as np
    if got is not None and expected is not None:
        diff = abs(got.image_array.astype('float') - expected.image_array.astype('float'))
        diffsize = np.sum(diff > 0)
        masksize = np.sum(expected.image_array > 0)
        if diffsize / masksize <= 0.05:
            return True
    return False


def compare_images(file1, file2):
    if file1 is None and file2 is None:
        return True
    if file1 is not None and file2 is not None:
        return compare_mask_images(openImage(file1), openImage(file2))
    return False

def compare_python_objects(obj1, obj2, keys_func={}):
    bad_keys = []
    for key in keys_func:
        v1 = getattr(obj1, "key")
        v2 = getattr(obj2, "key")
        if not keys_func[key](v1, v2):
            bad_keys.append(key)
    return bad_keys

def match_video_segments(expected, actual):
    """

    :param expected:
    :param actual:
    :return:
    @type expected: list of VideoSegment
    @type actual:list of VideoSegment
    """
    matched = {}
    errors = []

    for expected_pos in range(len(expected)):
        expected_segment = expected[expected_pos]
        for act_pos in range(len(actual)):
            if act_pos in matched:
                continue
            actual_segment = actual[act_pos]
            if actual_segment.startframe == expected_segment.startframe and \
                actual_segment.media_type == expected_segment.media_type:
                matched[act_pos] = expected_pos
                ok = actual_segment.endframe == expected_segment.endframe and \
                 abs(actual_segment.starttime - expected_segment.starttime) < expected_segment.rate and \
                 abs(actual_segment.endtime - expected_segment.endtime) < expected_segment.rate and \
                 abs(actual_segment.rate - expected_segment.rate) < 0.01
                if not ok:
                    errors.append(
                        'Got mismatched value in actual video segment {} vs. expected segment {}'.format(act_pos,
                                                                                                         expected_segment))
    for pos in range(len(actual)):
        if pos not in matched:
            errors.append('Unexpected value in video segement {}'.format(pos))
    for pos in range(len(expected)):
        if len([match_pos for match_pos in matched.values() if pos == match_pos]) == 0:
            errors.append('Unmatched value in video segement {}'.format(pos))
    return errors

def compare_video_segments(segments1, segments2):
    return len(match_video_segments(segments1, segments2)) == 0

def compare_probes(probe1, probe2):
    return compare_python_objects(probe1, probe2, keys_func={
        'donorBaseNodeId': lambda x, y: x == y,
        'edgeId': lambda x, y: x == y,
        'targetBaseNodeId': lambda x, y: x == y,
        'finalNodeId': lambda x, y: x == y,
        'targetChangeSizeInPixels': lambda x, y: x == y,
        'finalImageFileName': lambda x, y: x == y,
        'donorMaskFileName': lambda x, y: compare_images(x, y),
        'targetMaskFileName': lambda x, y: compare_images(x, y),
        'donorVideoSegments': lambda x, y: compare_video_segments(x, y),
        'targetVideoSegments': lambda x, y: compare_video_segments(x, 7)
    })
