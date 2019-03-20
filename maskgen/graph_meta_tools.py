# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import logging

from maskgen import ffmpeg_api
from maskgen.cv2api import cv2api_delegate
from maskgen.support import getValue
from maskgen.tool_set import GrayBlockReader, fileType
from maskgen.video_tools import get_shape_of_video, get_frame_time, getMaskSetForEntireVideo, \
    getMaskSetForEntireVideoForTuples, MetaDataLocator, get_end_time_from_segment, get_start_frame_from_segment, \
    get_frames_from_segment, get_rate_from_segment, get_start_time_from_segment, get_end_frame_from_segment,\
    get_type_of_segment, update_segment, create_segment, get_error_from_segment, get_file_from_segment,transfer_masks


def get_meta_data_change_from_edge(edge, expectedType='video'):
    """
    Inspect edge to see if vido meta-data changed such that the frame count is different
    as would be the case in a frame rate change.
    :param edge:
    :param expectedType:
    :return:
    """
    changeFrame = None
    changeDuration = None
    changeRate = None
    if 'metadatadiff' in edge and expectedType == 'video':
        change = getValue(edge,'metadatadiff.video.nb_frames',('x',0,0))
        changeFrame =  change if change[0] == 'change' else None
        change = getValue(edge, 'metadatadiff.video.duration', ('x', 0, 0))
        changeDuration = change if change[0] == 'change' else None
        change = getValue(edge, 'metadatadiff.video.r_frame_rate', getValue(edge, 'metadatadiff.video.avg_frame_rate',('x', 0, 0)))
        changeRate = change if change[0] == 'change' else None

    if not changeFrame and not changeDuration:
        return None

    try:
        if changeFrame and changeDuration and changeRate:
            if '/' in str(changeRate[2]):
                parts = changeRate[2].split('/')
                changeRate = float(parts[0]) / float(parts[1])
            else:
                changeRate = float(changeRate[2])
            return int(changeFrame[1]), \
                   float(changeDuration[1]) * 1000.0, \
                   int(changeFrame[2]), \
                   float(changeDuration[2]) * 1000.0, \
                   changeRate
    except:
        pass
    return None


class ExtractorMetaDataLocator(MetaDataLocator):
    def __init__(self, extractor, source):
        MetaDataLocator.__init__(self)
        self.extractor = extractor
        self.source = source

    def get_meta(self, with_frames=False, show_streams=True, media_types=['video']):
        return self.extractor.getVideoMeta(self.source,
                                           show_streams=show_streams,
                                           with_frames=with_frames,
                                           media_types=media_types)

    def get_filename(self):
        return self.extractor.getNodeFile(self.source)

    def get_frame_attribute(self, name, default=None, audio=False):
        return self.extractor.getVideoMetaItem(self.source, name, default=default, audio=audio)

def _match_stream(meta, streams):
    """

    :param current:
    :param streams: list of meta
    :return:
    """

    def __label(meta):
        return getValue(meta, 'codec_type', 'na') + getValue(meta, 'channel_layout', 'na')

    for item in streams:
        if __label(meta) == __label(item):
            return item
    return None


class MetaDataExtractor:
    def __init__(self, graph=None):
        self.graph = graph

    def __get_cache_from_graph(self, source):
        node = self.graph.get_node(source)
        if node is not None:
            return getValue(node, 'media', {})
        return {}

    def getVideoMetaItem(self, source, attribute, default=None, audio=False):
        """
        Featch meta data, overwriting any keys from the cache in the instance graph's node identified by source.
        :param source: source node id
        :param with_frames:
        :param show_streams:
        :param media_types:
        :return:
        """

        node_meta = self.__get_cache_from_graph(source)
        matched_value = None
        match_codec = 'video' if not audio else 'audio'
        for item in node_meta:
            if getValue(item, 'codec_type') == match_codec and matched_value is None:
                matched_value =  getValue(item,attribute)
        if matched_value is not None:
            return matched_value
        source_file = self.graph.get_image_path(source)
        if fileType(source_file) not in ['audio','video']:
            return default
        return ffmpeg_api.get_frame_attribute(source_file, attribute, default=default, audio=audio)


    def getVideoMeta(self, source, with_frames=False, show_streams=True, media_types=['video', 'audio']):
        """
        Featch meta data, overwriting any keys from the cache in the instance graph's node identified by source.
        :param source: source node id
        :param with_frames:
        :param show_streams:
        :param media_types:
        :return:
        """
        source_file = self.graph.get_image_path(source)
        meta, frames = ffmpeg_api.get_meta_from_video(source_file, with_frames=with_frames, show_streams=show_streams,
                                                      media_types=media_types)
        node_meta = self.__get_cache_from_graph(source)
        for item in meta:
            match = _match_stream(item, node_meta)
            if match is not None:
                item.update(match)
        return meta, frames

    def getNodeFileType(self, nodeid):
        return self.graph.getNodeFileType(nodeid)

    def getNodeFile(self, nodeid):
        return self.graph.get_image_path(nodeid)

    def getNodeSize(self, nodeid):
        node = self.graph.get_node(nodeid)
        # even the video case, this should be cached!
        if node is not None and 'shape' in node:
            return (node['shape'][1], node['shape'][0])
        else:
            return get_shape_of_video(self.graph.get_image_path(nodeid))

    def get_video_orientation_change(self, source, target):
        source_data = self.getVideoMeta(source, show_streams=True)[0]
        donor_data = self.getVideoMeta(target, show_streams=True)[0]

        source_channel_data = source_data[ffmpeg_api.get_stream_indices_of_type(source_data, 'video')[0]]
        target_channel_data = donor_data[ffmpeg_api.get_stream_indices_of_type(donor_data, 'video')[0]]

        return int(getValue(target_channel_data, 'rotation', 0)) - int(getValue(source_channel_data, 'rotation', 0))

    def getMasksFromEdge(self, source, target, media_types, channel=0, startTime=None, endTime=None):
        """
        Currently prioritizes masks over entered.  This seems appropriate.  Adjust the software to
        produce masks consistent with recorded change.
        :param filename:q
        :param edge:
        :param media_types:
        :param channel:
        :param startTime:
        :param endTime:
        :return:
        """

        edge = self.graph.get_edge(source, target)
        if 'videomasks' in edge and \
                        edge['videomasks'] is not None and \
                        len(edge['videomasks']) > 0:
            return [mask for mask in edge['videomasks'] if mask['type'] in media_types]
        else:
            result = getMaskSetForEntireVideo(self.getMetaDataLocator(source),
                                              start_time=getValue(edge, 'arguments.Start Time',
                                                                  defaultValue='00:00:00.000')
                                              if startTime is None else startTime,
                                              end_time=getValue(edge, 'arguments.End Time')
                                              if endTime is None else endTime,
                                              media_types=media_types,
                                              channel=channel)
            if result is None or len(result) == 0:
                return None
        return result

    def getMetaDataLocator(self, source):
        return ExtractorMetaDataLocator(self, source)

    def getChangeInFrames(self, edge, meta_i, meta_o, source, target, expectedType='video'):

        if meta_i is None or meta_o is None:
            result = get_meta_data_change_from_edge(edge, expectedType=expectedType)
            if result is not None:
                return result
        else:
            change = getValue(meta_i, 'duration', None) != getValue(meta_o, 'duration', None) or \
                     getValue(meta_i, 'nb_frames', None) != getValue(meta_o, 'nb_frames', None) or \
                     getValue(meta_i, 'sample_rate', None) != getValue(meta_o, 'sample_rate', None) or \
                     getValue(meta_i, 'avg_frame_rate', None) != getValue(meta_o, 'avg_frame_rate', None) or \
                     getValue(meta_i, 'duration_ts', None) != getValue(meta_o, 'duration_ts', None)

            if not change:
                return None

        maskSource = getMaskSetForEntireVideoForTuples(self.getMetaDataLocator(source), media_types=[expectedType])
        maskTarget = getMaskSetForEntireVideoForTuples(self.getMetaDataLocator(target), media_types=[expectedType])
        return get_frames_from_segment(maskSource[0]), get_end_time_from_segment(maskSource[0]), \
               get_frames_from_segment(maskTarget[0]), get_end_time_from_segment(maskTarget[0]), \
               get_rate_from_segment(maskSource[0]), get_rate_from_segment(maskTarget[0])

    def create_video_for_audio(self, source, masks):
        """
        make a mask in video time for each audio mask in masks.
        in VFR case, uses ffmpeg frames to get nearest frame to timestamp.
        :param source: video file
        :param masks:
        :return: new set of masks
        """
        from math import floor
        from video_tools import get_frame_rate

        def _get_frame_time(frame):
            if 'pkt_pts_time' in frame.keys() and frame['pkt_pts_time'] != 'N/A':
                return float(frame['pkt_pts_time']) * 1000
            else:
                return float(frame['pkt_dts_time']) * 1000

        def _frame_distance(time_a, time_b):
            dist = time_a - time_b
            return abs(dist) if dist <= 0 else float('inf')

        meta_and_frames = self.getVideoMeta(source, show_streams=True, with_frames=False, media_types=['video'])
        hasVideo = ffmpeg_api.get_stream_indices_of_type(meta_and_frames[0], 'video')
        meta = meta_and_frames[0][0]
        isVFR = ffmpeg_api.is_vfr(meta)
        video_masks = [mask for mask in masks if get_type_of_segment(mask)== 'video']
        audio_masks = [mask for mask in masks if get_type_of_segment(mask) == 'audio']
        if len(video_masks) == 0 and hasVideo:
            entire_mask = getMaskSetForEntireVideoForTuples(self.getMetaDataLocator(source), media_types=['video'])[0]
            upper_bounds = (get_end_frame_from_segment(entire_mask), get_end_time_from_segment(entire_mask))
            new_masks = list(audio_masks)
            for mask in audio_masks:
                end_time = min(get_end_time_from_segment(mask), upper_bounds[1])
                new_mask = mask.copy()
                rate = get_frame_rate(self.getMetaDataLocator(source))
                if not isVFR:
                    start_frame = int(get_start_time_from_segment(mask) * rate / 1000.0) + 1
                    end_frame = int(end_time * rate / 1000.0)
                else:
                    video_frames = \
                    self.getVideoMeta(source, show_streams=True, with_frames=True, media_types=['video'])[1][0]
                    start_frame = video_frames.index(
                        min(video_frames, key=lambda x: _frame_distance(_get_frame_time(x), get_start_time_from_segment(mask)))) + 1
                    end_frame = video_frames.index(
                        min(video_frames, key=lambda x: _frame_distance(_get_frame_time(x), end_time))) + 1
                end_frame = min(end_frame, upper_bounds[0])
                update_segment(new_mask,
                               type= 'video-associate',
                               rate=rate,
                               endtime=end_time,
                               startframe=start_frame,
                               endframe=end_frame)
                new_masks.append(new_mask)
            return new_masks
        else:
            return masks


    def warpMask(self, video_masks, source, target, expectedType='video', inverse=False, useFFMPEG=False):
        """
        Tranform masks when the frame rate has changed.
        :param video_masks: ithe set of video masks to walk through and transform
        :param expectedType:
        :param video_masks:
        :return: new set of video masks
        """
        edge = self.graph.get_edge(source, target)
        meta_i, frames_i = self.getVideoMeta(source, show_streams=True, media_types=[expectedType])
        meta_o, frames_o = self.getVideoMeta(target, show_streams=True, media_types=[expectedType])
        indices_i = ffmpeg_api.get_stream_indices_of_type(meta_i, expectedType)
        indices_o = ffmpeg_api.get_stream_indices_of_type(meta_o, expectedType)
        if not indices_i or not indices_o:
            return video_masks
        index_i = indices_i[0]
        index_o = indices_o[0]
        isVFR = ffmpeg_api.is_vfr(meta_i[index_i]) or ffmpeg_api.is_vfr(meta_o[index_o])

        result = self.getChangeInFrames(edge,
                                        meta_i[index_i],
                                        meta_o[index_o],
                                        source,
                                        target,
                                        expectedType=expectedType)

        if result is None:
            return video_masks

        sourceFrames, sourceTime, targetFrames, targetTime, sourceRate, targetRate = result

        if sourceFrames == targetFrames and int(sourceTime*100) == int(targetTime*100):
            return video_masks

        def apply_change(existing_value, orig_rate, final_rate, inverse=False, round_value=True,
                         min_value=0,upper_bound=False):
            # if round_value, return a tuple of value plus rounding error
            import math
            multiplier = -1.0 if inverse else 1.0
            adjustment = existing_value * math.pow(final_rate / orig_rate, multiplier)
            if round_value:
                v = max(min(round(adjustment),final_rate) if upper_bound else round(adjustment),min_value)
                e = abs(adjustment - v)
                return int(v), e
            return max(min(adjustment,final_rate) if upper_bound else adjustment,min_value)

        def adjustPositionsFFMPEG(meta, video_frames, hits):
            rate = ffmpeg_api.get_video_frame_rate_from_meta([meta], [video_frames])
            aptime = 0
            lasttime = 0
            hitspos = 0
            start_mask = None
            for pos in range(0, len(video_frames)):
                aptime = get_frame_time(video_frames[pos], aptime, rate)
                while hitspos < len(hits) and aptime > hits[hitspos][0]:
                    mask = hits[hitspos][2]
                    element = hits[hitspos][1]
                    error = abs(aptime - hits[hitspos][0])
                    if element == 'starttime':
                        update_segment(mask,
                                       starttime=lasttime,
                                       startframe=pos,
                                       error=error + get_error_from_segment(mask))
                        start_mask = mask
                    else:
                        # for error, only record the error if not recorded
                        update_segment(mask,
                                       endtime=lasttime,
                                       endframe=pos,
                                       error=(error if start_mask != mask else 0) + get_error_from_segment(mask))
                    hitspos += 1
                lasttime = aptime
            return mask

        def adjustPositions(video_file, hits):
            # used if variable frame rate
            frmcnt = 0
            hitspos = 0
            last = 0
            cap = cv2api_delegate.videoCapture(video_file)
            try:
                while cap.grab() and hitspos < len(hits):
                    frmcnt += 1
                    aptime = cap.get(cv2api_delegate.prop_pos_msec)
                    while hitspos < len(hits) and aptime > hits[hitspos][0]:
                        mask = hits[hitspos][2]
                        element = hits[hitspos][1]
                        error = max(abs(last - hits[hitspos][0]), abs(aptime - hits[hitspos][0]))
                        if element == 'starttime':
                            update_segment(mask,
                                           starttime =last,
                                           startframe=frmcnt,
                                           error = error)
                        else:
                            update_segment(mask,
                                           endtime =last,
                                           endframe=frmcnt,
                                           error = max(error, get_error_from_segment(mask)))
                        hitspos += 1
                    last = aptime
            finally:
                cap.release()
            return mask

        new_mask_set = []
        hits = []
        # First adjust all the frame and time references by the total change in the video.
        # In most cases, the length of the video in time changes by a small amount which is distributed
        # across all the masks
        for mask_set in video_masks:
            if 'type' in mask_set and mask_set['type'] != expectedType:
                new_mask_set.append(mask_set)
                continue
            startframe, error_start = apply_change(get_start_frame_from_segment(mask_set), float(sourceFrames),
                                       float(targetFrames), inverse=inverse, round_value=True,min_value=1)
            endframe, error_end = apply_change(get_end_frame_from_segment(mask_set),
                                               float(sourceFrames),
                                               float(targetFrames),
                                               inverse=inverse,
                                               min_value=1,
                                               round_value=True,
                                               upper_bound=True)
            endtime = apply_change(get_end_time_from_segment(mask_set), float(sourceTime), targetTime, inverse=inverse,
                                             round_value=False)
            starttime = apply_change(get_start_time_from_segment(mask_set),
                                     sourceTime,
                                     targetTime,
                                     inverse=inverse,
                                     round_value=False,
                                     upper_bound=True)

            try:
                if endframe == int(getValue(meta_o[index_o], 'nb_frames', 0)) and \
                                float(getValue(meta_o[index_o], 'duration', 0)) > 0:
                    endtime = float(getValue(meta_o[index_o], 'duration', 0)) * 1000.0
                elif endtime > targetTime:
                    message = '{} exceeded target time of {} for {}'.format(sourceTime, target, targetTime)
                    if (endtime - targetTime) > 300:
                        logging.getLogger('maskgen').error(message
                            )
                    else:
                        logging.getLogger('maskgen').warn(message
                        )
                    endtime=targetTime - (1000.0/targetRate)
                    endframe=targetFrames-1
            except:
                pass
            change = create_segment(rate=sourceRate if inverse else targetRate,
                                    type=get_type_of_segment(mask_set),
                                    starttime=starttime,
                                    startframe=startframe,
                                    error=get_error_from_segment(mask_set) + (max(error_start, error_end) / targetRate * 1000.0),
                                    endtime=endtime,
                                    endframe=endframe,
                                    videosegment=get_file_from_segment(mask_set))
            new_mask_set.append(change)
            hits.append((get_start_time_from_segment(change), 'starttime', change))
            hits.append((get_end_time_from_segment(change), 'endime', change))

        # only required when one of the two videos is variable rate
        hits = sorted(hits)

        if isVFR:
            if useFFMPEG:
                meta_r, frames_r = self.getVideoMeta(source if inverse else target,
                                                     show_streams=True,
                                                     with_frames=True,
                                                     media_types=[expectedType])
                index_r = ffmpeg_api.get_stream_indices_of_type(meta_o, expectedType)[0]
                adjustPositionsFFMPEG(meta_r[index_r], frames_r[index_r], hits)
            else:
                adjustPositions(self.getNodeFile(source) if inverse else self.getNodeFile(target), hits)

        transfer_masks(video_masks,new_mask_set,
                       frame_time_function= lambda  x,y: y+(1000.0/targetRate),
                       frame_count_function = lambda  x,y: y+1)
        return new_mask_set


class GraphProxy:
    def __init__(self, source, target, edge={}, source_node={}, target_node={}):
        self.source = source
        self.target = target
        self.edge = edge
        self.source_node = source_node
        self.target_node = target_node

    def get_edge(self, source, target):
        if source == self.source and self.target == target:
            return self.edge
        return {}

    def get_node(self, node_id):
        if node_id == self.source:
            return self.source_node
        else:
            return self.target_node

    def get_image_path(self, node_id):
        return node_id
