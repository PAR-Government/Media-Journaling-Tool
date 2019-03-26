# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

# NOTE: ZipReader/Capture are in tool_set for BC.

from tool_set import getMilliSeconds, audiofiletypes
from ffmpeg_api import get_meta_from_video

from zipfile import ZipFile
import os

class Positions:

    def __init__(self, positions=[], fps=48000):
        self.positions = positions
        self.fps = fps

    def sub_positions(self, start_time, end_time):
        start_position = next((p for p in range(0, len(self.positions)) if self.positions[p][0] >= start_time), len(self.positions)-1)
        if end_time < start_time:
            end_position = len(self.positions)
        else:
            end_position = next((p for p in range(0, len(self.positions)) if self.positions[p][0] >= end_time), len(self.positions))
        return Positions([self.positions[p] for p in range(max(0,start_position-1),end_position)])

    def size(self):
        return len(self.positions)

    @staticmethod
    def to_segment(position, is_time=True, fps=48000):
        frame_time = getMilliSeconds(position) if is_time else ((position - 1)/fps * 1000.0)
        frame_number = int(frame_time * fps / 1000.0) + 1 if is_time else position
        return frame_time, frame_number

    @staticmethod
    def read(position_file, is_time=True, fps=48000):
        """

        :param position_file:
        :param is_time: if the first row is a time (00:00:00.000000) or a frame number
        :param fps:
        :return:
        """
        import csv
        with open(position_file,'r') as fp:
            reader = csv.reader(fp)
            return Positions([Positions.to_segment(row[0],is_time=is_time,fps=fps)+ (row[1],) for row in reader], fps=fps)

    def _get_duration(self, position_file):
        return 0

    def _get_meta_data(self,position_data):
        end_time = self._get_duration(position_data[2])
        end_position = int(end_time*self.fps/1000.0)+1
        return self.start_time, int(self.start_time*self.fps/1000.0)+1,end_time,end_position

    def get_segments(self, initial_start_time=0, final_end_time=-1):
        subs = self.sub_positions(initial_start_time, final_end_time).positions
        start_time = initial_start_time
        segs = []
        for p in range(0,len(subs)-1):
            # could start in the middle of the first
            seg_start = max(start_time, subs[p][0])
            end_time = self._get_duration(subs[p][2])
            # could end before the start of next
            seg_end = min(seg_start+end_time, subs[p+1][0]-1.0/self.fps)
            segs.append((seg_start, int(seg_start*self.fps/1000.0)+1, seg_end, int(seg_end*self.fps/1000.0)+1))
        p = len(subs)-1
        seg_start = subs[p][0]
        seg_end = seg_start + self._get_duration(subs[p][2])
        segs.append((seg_start,
                    int(seg_start * self.fps / 1000.0) + 1,
                    seg_end,
                    int(seg_end * self.fps / 1000.0) + 1))
        return segs

    def validate_duration(self, some_file, final_end_time=-1, tolerance=1):
        """
        Is the file within a tolerance of duration from expected
        :param some_file:
        :param initial_start_time:
        :param final_end_time:
        :return:
        """
        seg_end, some_file_duration = self.get_durations(some_file,final_end_time=final_end_time)
        return (seg_end - some_file_duration) <= tolerance

    def get_total_duration(self):
        return self.positions[-1][0] + self._get_duration(self.positions[-1][2])

    def get_durations(self, some_file, final_end_time=-1):
        """
        :param some_file:
        :param initial_start_time:
        :param final_end_time:
        :return: duration of zip and duration of some file
        """
        subs = self.sub_positions(0, final_end_time).positions
        some_file_duration = self._get_duration(some_file)
        seg_start = subs[-1][0]
        seg_end = seg_start + self._get_duration(subs[-1][2])
        return seg_end, some_file_duration

    def get_file(self, name):
        return name

    def validate_content(self, some_file, final_end_time=-1, content_extractor=None):
        """
        Validate that the start of every segment in somefile matches the postion data from the zip file
        :param some_file:
        :param initial_start_time:
        :param final_end_time:
        :param tolerance:
        :return:
        """
        subs = self.sub_positions(0, final_end_time).positions
        other_extractor = content_extractor(some_file)
        for sub in subs:
            other_extractor.sinkToTime(sub[0])
            sub_extractor = content_extractor(self.get_file(subs[2]))
            if other_extractor.getData() != sub_extractor.getData():
                return False
        return True

    def get_meta_data(self,position=-1):
        """
        :return:  start time,start frame, end time, end frame
        @rtype: (float, int, float, int)
        """
        return self.get_meta_data(self.positions[position])

class AudioPositions(Positions):

    def __init__(self, zip_filename, position_file_name=None, is_time=True, fps=48000,audio_metadata_extractor= None):
        import re
        self.zip_filename = zip_filename
        self.fps = fps
        self.audio_metadata_extractor = self.audio_metadata_extractor if audio_metadata_extractor is None else audio_metadata_extractor
        self.dir = os.path.dirname(os.path.abspath(self.zip_filename))
        file_type_matcher = re.compile(
            '.*\.(' + '|'.join([ft[1][ft[1].rfind('.') + 1:] for ft in audiofiletypes]) + ')')
        self.myzip = ZipFile(zip_filename, 'r')
        self.names = [name for name in self.myzip.namelist() if len(file_type_matcher.findall(name.lower())) > 0 and \
                      os.path.basename(name) == name]
        self.file_meta = {}
        if position_file_name is not None:
            Positions.__init__(self,Positions.read(position_file_name, is_time=is_time, fps=48000).positions,fps=48000)
            for position in self.positions:
                if position[2] not in self.names:
                    raise ValueError('Missing {} from audio zip file'.format(position[2]))
        else:
            meta = self.audio_metadata_extractor(self.names[0])
            self.fps = int(meta['sample_rate'])
            positions = []
            positions.append(
                Positions.to_segment(0, is_time=True, fps=self.fps) + (self.names[0],))
            last = 0
            for name_pos in range(len(self.names)-1):
                # get duration of last for start of next
                if name_pos > 0:
                    meta = self.audio_metadata_extractor(self.names[name_pos])
                last = float(meta['duration'])*1000.0 + last
                if int(meta['sample_rate']) != self.fps:
                    raise ValueError('Mismatched sample rate {} from audio zip file {}'.format(self.fps,int(meta['sample_rate']) ))
                positions.append(Positions.to_segment(last, is_time=True, fps=int(meta['sample_rate'])) + (self.names[name_pos+1],))
            Positions.__init__(self,positions, fps=fps)

    def audio_metadata_extractor(self, filename):
        place = self.get_file(filename)
        meta = get_meta_from_video(place, show_streams=True, media_types=['audio'])[0]
        return  [x for x in meta if len(x) > 0][0]

    def get_file(self, name):
        path  = os.path.join(self.dir,name)
        if os.path.exists(path):
            return path
        if os.path.exists(name):
            return name
        return self.myzip.extract(name, self.dir)

    def _get_duration(self, position_file):
        if os.path.basename(position_file) not in self.file_meta:
            meta = self.audio_metadata_extractor(position_file)
            self.file_meta[os.path.basename(position_file)] = meta
        else:
            meta = self.file_meta[os.path.basename(position_file)]
        return float(meta['duration'])*1000.0

    def isOpened(self):
        #TODO: check names, what else
        return True

    def release(self):
        import shutil
        shutil.rmtree(self.dir)
        self.myzip.close()
