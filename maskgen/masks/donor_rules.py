# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================
from maskgen.image_wrap import ImageWrapper
from maskgen.support import getValue
from maskgen.tool_set import interpolateMask
from maskgen.video_tools import get_rate_from_segment, get_start_time_from_segment, \
    get_end_time_from_segment, update_segment, get_type_of_segment


#===================================================
#
# Defines Donor factory function associated with donor_processor of an Operation.
# The factory creates A Donor object that responds to the arguments (arguments method)
# required for the donor operation
# and mask generating component of the donor (create method).
#
# donors edge is defined between nodes donor_start and donor_end.
# The donor_end is also the target of the manipulation that used the donor (e.g. Paste).
# The parent (source) of the manipulation is the parent_of_end.
# THe mask and manipulation from the associated manipulation can be used in donor computation.
#
#===================================================


def _pre_select_mask(graph, start, startIm):
    from PIL import Image
    predecessors = graph.predecessors(start)
    for pred in predecessors:
        edge = graph.get_edge(pred, start)
        if edge['op'] == 'SelectRegion':
            mask = graph.get_edge_image(pred, start, 'maskname').invert()
            if mask.size != startIm.size:
                mask = mask.resize(startIm.size, Image.ANTIALIAS)
            return mask

def donothing_processor(graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return DoNothingDonor()

def donothing_stream_processor(graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return DoNothingStreamDonor()


class DoNothingStreamDonor:

    def arguments(self):
        return {}

    def create(self,
               arguments={},
               invert=False):
        return []

class DoNothingDonor:

    def arguments(self):
        return {}

    def create(self,
               arguments={},
               invert=False):
        return None

def alpha_stream_processor(graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return AlphaDonor(graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

class AlphaDonor:

    """
    USE SIFT/RANSAC TO FIND DONOR MASK
    IF ALPHA CHANNEL IS AVAILABLE, THEN USE THAT INSTEAD
    """

    def __init__(self,graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        self.graph = graph
        self.donor_start = donor_start
        self.donor_end = donor_end
        self.parent_of_end = parent_of_end
        self.startIm = startImTuple[0]
        self.destIm = destImTuple[0]
        self.startFileName = startImTuple[1]
        self.destFileName = destImTuple[1]

    def arguments(self):
        return {}

    def create(self,
               arguments={},
               invert=False):
        mask = _pre_select_mask(self.graph, self.donor_start, self.startIm)
        mask = self.startIm.to_mask().invert() if mask is None else mask
        return mask.invert() if invert else mask


def image_interpolate(graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return InterpolateDonor(graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

class InterpolateDonor:

    """
    USE SIFT/RANSAC TO FIND DONOR MASK
    IF ALPHA CHANNEL IS AVAILABLE, THEN USE THAT INSTEAD
    """

    def __init__(self,graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        self.graph = graph
        self.donor_start = donor_start
        self.donor_end = donor_end
        self.parent_of_end = parent_of_end
        self.startIm = startImTuple[0]
        self.destIm = destImTuple[0]
        self.startFileName = startImTuple[1]
        self.destFileName = destImTuple[1]

    def arguments(self):
        if self.startIm.has_alpha():
            default = 'None'
        else:
            default = 'RANSAC-4'
        predecessors = self.graph.predecessors(self.donor_start)
        for pred in predecessors:
            edge = self.graph.get_edge(pred, self.donor_start)
            if edge['op'].startswith('Select'):
                default = 'None'

        return {
            "homography": {
                "type": "list",
                "source": "image",
                "defaultvalue": default,
                "values": [
                    "None",
                    "Map",
                    "All",
                    "LMEDS",
                    "RANSAC-3",
                    "RANSAC-4",
                    "RANSAC-5"
                ],
                "trigger mask": True,
                "description": "Tune transform creation for composite mask generation"
            },
            "homography max matches": {
                "type": "int[20:10000]",
                "defaultvalue":2000,
                "description": "Maximum number of matched feature points used to compute the homography.",
                "trigger mask": True
            }
        }


    def create(self,
               arguments={},
               invert=False):
        import numpy as np
        if getValue(arguments,'homography','None') == 'None':
            if self.startIm.has_alpha():
                img_array = np.asarray(self.startIm)
                mask = np.copy(img_array[:,:,3])
                #accept the alpha channel as what is kept
                mask[mask>0]  = 255
                #invert since 0 in the donor mask indicates the donor pixels
                return ImageWrapper(mask).invert()
            # use the pre select mask (inverted) as the selection...invert what was removed to be what is kept
            return _pre_select_mask(self.graph, self.donor_start, self.startIm)
        mask = self.graph.get_edge_image(self.parent_of_end, self.donor_end, 'arguments.pastemask')
        if mask is None:
            mask = self.graph.get_edge_image(self.parent_of_end, self.donor_end, 'maskname')
        mask, analysis = interpolateMask(
            mask,
            self.startIm,
            self.destIm,
            arguments=arguments,
            invert=invert)
        if mask is not None and mask.shape != (0, 0):
            mask = ImageWrapper(mask)
        else:
            mask = None
        return mask

def video_interpolate(graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return VideoInterpolateDonor(graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

class VideoInterpolateDonor:
    def arguments(self):
        return {
            "homography": {
                "type": "list",
                "source": "image",
                "values": [
                    "None",
                    "Map",
                    "All",
                    "LMEDS",
                    "RANSAC-3",
                    "RANSAC-4",
                    "RANSAC-5"
                ],
                "trigger mask": True,
                "description": "Tune transform creation for composite mask generation"
            }
        }

    def __init__(self, graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        """
        :param graph:
        :param donor_start:
        :param donor_end:
        :param parent_of_end:
        :param startImTuple:
        :param destImTuple:
        @type graph: ImageGraph
        """
        self.graph = graph
        self.donor_start = donor_start
        self.donor_end = donor_end
        self.parent_of_end = parent_of_end
        self.startIm = startImTuple[0]
        self.destIm = destImTuple[0]
        self.startFileName = startImTuple[1]
        self.destFileName = destImTuple[1]

    def create(self,
               arguments={},
               invert=False):
        from maskgen.video_tools import interpolateMask
        import os
        from maskgen.tool_set import shortenName
        """
          Used for Donor video or images, the mask recording a 'donation' is the inversion of the difference
          of the Donor image and its parent, it exists.
          Otherwise, the donor image mask is the donor image (minus alpha channels):
        """
        edge = self.graph.get_edge(self.parent_of_end, self.donor_end)
        return interpolateMask(
            os.path.join(self.graph.dir, shortenName(self.donor_start + '_' + self.donor_end, '_mask')),
            self.graph.dir,
            edge['videomasks'],
            self.startFileName,
            self.destFileName,
            arguments=arguments)


def video_donor(graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return VideoDonor(graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

def video_without_audio_donor(graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return VideoDonorWithoutAudio(graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

class VideoDonor:

    def __init__(self, graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        """
        :param graph:
        :param donor_start:
        :param donor_end:
        :param parent_of_end:
        :param startImTuple:
        :param destImTuple:
        @type graph: ImageGraph
        """
        self.graph = graph
        self.donor_start = donor_start
        self.donor_end = donor_end
        self.parent_of_end = parent_of_end
        self.startIm = startImTuple[0]
        self.destIm = destImTuple[0]
        self.startFileName = startImTuple[1]
        self.destFileName = destImTuple[1]

    def _base_arguments(self):
        return {
            "include audio": {
                "type": "yesno",
                "defaultvalue": "no",
                "trigger mask": True,
                "description": "Is Audio Donated."
            },
            "Start Time": {
                "type": "frame_or_time",
                "defaultvalue": 1,
                "trigger mask": True,
                "description": "Start frame number"
            },
            "End Time": {
                "type": "frame_or_time",
                "defaultvalue": 0,
                "trigger mask" : True,
                "description": "End frame number. Leave 0 if ALL"
            }
        }

    def arguments(self):
        args = self._base_arguments()
        predecessors = self.graph.predecessors(self.donor_start)
        for pred in predecessors:
            edge = self.graph.get_edge(pred, self.donor_start)
            if edge['op'].startswith('Select'):
                args['Start Time']['defaultvalue'] = getValue(edge,'arguments.Start Time',"1")
                end_def = getValue(edge, 'arguments.End Time', None)
                if end_def is not None:
                    args['End Time']['defaultvalue'] = end_def
        return args

    def create(self,
               arguments={},
               invert=False):
        from maskgen.tool_set import getMilliSecondsAndFrameCount
        media_types = ['video', 'audio'] if getValue(arguments, 'include audio', 'no') == 'yes' else ['video']

        from maskgen.video_tools import getMaskSetForEntireVideoForTuples, FileMetaDataLocator
        end_time_tuple = getMilliSecondsAndFrameCount(getValue(arguments, 'End Time', "00:00:00"))
        start_time_tuple = getMilliSecondsAndFrameCount(getValue(arguments, 'Start Time', '00:00:00'))
        video_set= getMaskSetForEntireVideoForTuples(FileMetaDataLocator(self.startFileName),
                                                     start_time_tuple=start_time_tuple,
                                                     end_time_tuple=end_time_tuple if end_time_tuple[1] > start_time_tuple[1] else None,
                                                     media_types=media_types)
        audio_segments = [x for x in video_set if get_type_of_segment(x) == 'audio']
        video_segments = [x for x in video_set if get_type_of_segment(x) == 'video']

        if getValue(arguments, 'include audio', 'no') == 'yes':
            for audio_segment in audio_segments:
               video_segment = video_segments[0] if len(video_segments) > 0 else audio_segment
               update_segment(audio_segment,
                              type='audio',
                              starttime=get_start_time_from_segment(video_segment),
                              endtime=get_end_time_from_segment(video_segment),
                              startframe=int(get_start_time_from_segment(video_segment) * get_rate_from_segment(audio_segment)/1000.0),
                              endframe=int(get_end_time_from_segment(video_segment)* get_rate_from_segment(audio_segment)/1000.0)+1)
        return video_set

class VideoDonorWithoutAudio(VideoDonor):

    def __init__(self, graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        """
        :param graph:
        :param donor_start:
        :param donor_end:
        :param parent_of_end:
        :param startImTuple:
        :param destImTuple:
        @type graph: ImageGraph
        """
        VideoDonor.__init__(self,graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

    def _base_arguments(self):
        return {
            "Start Time": {
                "type": "frame_or_time",
                "defaultvalue": 1,
                "description": "Start frame number"
            },
            "End Time": {
                "type": "frame_or_time",
                "defaultvalue": 0,
                "description": "End frame number. Leave 0 if ALL"
            }
        }

class GeneralStreamDonor:

    def __init__(self, graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        """
        :param graph:
        :param donor_start:
        :param donor_end:
        :param parent_of_end:
        :param startImTuple:
        :param destImTuple:
        @type graph: ImageGraph
        """
        self.graph = graph
        self.donor_start = donor_start
        self.donor_end = donor_end
        self.parent_of_end = parent_of_end
        self.startIm = startImTuple[0]
        self.destIm = destImTuple[0]
        self.startFileName = startImTuple[1]
        self.destFileName = destImTuple[1]

    def media_types(self):
        return ['audio','video']

    def arguments(self):
        args = self._base_arguments()
        edge = self.graph.get_edge(self.donor_start,self.donor_end)
        args['Start Time']['defaultvalue'] = getValue(edge,'arguments.Start Time',"1")
        end_def = getValue(edge, 'arguments.End Time', None)
        if end_def is not None:
            args['End Time']['defaultvalue'] = end_def
        return args

    def _base_arguments(self):
        return {
            "Start Time": {
                "type": "time",
                "defaultvalue": "00:00:00.000000",
                "description": "Start time"
            },
            "End Time": {
                "type": "time",
                "defaultvalue": "00:00:00.000000",
                "description": "End time. Leave 00:00:00.000000 if ALL"
            }
        }

    def create(self,
               arguments={},
               invert=False):
        from maskgen.video_tools import getMaskSetForEntireVideoForTuples, FileMetaDataLocator
        from maskgen.tool_set import getMilliSecondsAndFrameCount
        end_time_tuple = getMilliSecondsAndFrameCount(getValue(arguments, 'End Time', "00:00:00"))
        start_time_tuple = getMilliSecondsAndFrameCount(getValue(arguments, 'Start Time', '00:00:00'))
        return getMaskSetForEntireVideoForTuples(FileMetaDataLocator(self.startFileName),
                                                 start_time_tuple=start_time_tuple,
                                                 end_time_tuple=end_time_tuple if end_time_tuple[0] > 0 else None,
                                                 media_types=self.media_types())


def audio_donor_processor(graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return AudioDonor(graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

def audio_sample_donor_processor(raph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return SampleAudioDonor(raph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

class AudioDonor(GeneralStreamDonor):

    def __init__(self, graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        """
        :param graph:
        :param donor_start:
        :param donor_end:
        :param parent_of_end:
        :param startImTuple:
        :param destImTuple:
        @type graph: ImageGraph
        """
        GeneralStreamDonor.__init__(self,graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple)


    def media_types(self):
        return ['audio']

class SampleAudioDonor(AudioDonor):


    def __init__(self, graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        """
        :param graph:
        :param donor_start:
        :param donor_end:
        :param parent_of_end:
        :param startImTuple:
        :param destImTuple:
        @type graph: ImageGraph
        """
        AudioDonor.__init__(self,graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

    #
    # def create(self,
    #            arguments={},
    #            invert=False):
    #
    #     from maskgen.tool_set import getMilliSecondsAndFrameCount,VidTimeManager
    #     from maskgen.video_tools import audioDonor
    #
    #     from maskgen.video_tools import getMaskSetForEntireVideoForTuples, FileMetaDataLocator
    #     end_time_tuple = getMilliSecondsAndFrameCount(getValue(arguments, 'End Time', "00:00:00"))
    #     start_time_tuple = getMilliSecondsAndFrameCount(getValue(arguments, 'Start Time', '00:00:00'))
    #     audio_set= getMaskSetForEntireVideoForTuples(FileMetaDataLocator(self.startFileName),
    #                                                  start_time_tuple=start_time_tuple,
    #                                                  end_time_tuple=end_time_tuple if end_time_tuple[1] > start_time_tuple[1] else None,
    #                                                  media_types=['audio'])
    #     time_manager = VidTimeManager(start_time_tuple,end_time_tuple)
    #     try:
    #         return [audioDonor(self.startFileName, self.destFileName, time_manager, arguments={})]
    #     except:
    #         return audio_set

def all_audio_processor(graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return AllAudioStreamDonor(graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

class AllAudioStreamDonor(AudioDonor):

    def __init__(self, graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        """
        :param graph:
        :param donor_start:
        :param donor_end:
        :param parent_of_end:
        :param startImTuple:
        :param destImTuple:
        @type graph: ImageGraph
        """
        AudioDonor.__init__(self,graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

    def arguments(self):
        return {}

def all_stream_processor(graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
    return AllStreamDonor(graph, donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

class AllStreamDonor(GeneralStreamDonor):

    def __init__(self, graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple):
        """
        :param graph:
        :param donor_start:
        :param donor_end:
        :param parent_of_end:
        :param startImTuple:
        :param destImTuple:
        @type graph: ImageGraph
        """
        GeneralStreamDonor.__init__(self,graph,donor_start, donor_end, parent_of_end, startImTuple, destImTuple)

    def arguments(self):
        return {}

