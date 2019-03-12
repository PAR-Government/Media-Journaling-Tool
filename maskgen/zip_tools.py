# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

# NOTE: ZipReader/Capture are in tool_set for BC.

from tool_set import zipFileType, ZipWriter, ZipCapture, getMilliSeconds,filetypes

import uuid
from zipfile import ZipFile
import os

class Positions:

    def __init__(self, positions=[], fps=48000, start_time = None, end_time = None):
        self.positions = positions
        self.fps = fps
        if start_time is None:
            if positions:
                self.start_time = self.positions[0][0]
            else:
                self.start_time = 0
        else:
            self.start_time = 0
        self.end_time = end_time

    def sub_positions(self, start_time, end_time):
        start_positions = [p for p in self.positions if p[0] >= start_time]
        return Positions([p for p in start_positions if p[0] <= end_time], start_time, end_time)

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
            return Positions([Positions.to_segment(float(row[0]),is_time=is_time,fps=fps)+ (row[1],) for row in reader], fps=fps)

    def get_meta_data(self, duration_func):
        """
        :param duration_func:
        :return:  start time,start frame, end time, end frame
        @type duration_func: ()
        @rtype: (float, int, float, int)
        """
        end_time = duration_func(self.positions[-1][2])
        end_position = int(end_time*self.fps/1000.0)+1
        return self.start_time, int(self.start_time*self.fps/1000.0)+1,end_time,end_position


class AudioPositions(Positions):

    def __init__(self, zip_filename, position_file_name=None, is_time=True, fps=48000):
        import re
        Positions.__init__(Positions.to_segment(position_file_name),is_time=is_time, fps=fps)
        self.zip_filename = zip_filename
        self.dir = os.path.dirname(os.path.abspath(self.filename))
        file_type_matcher = re.compile('.*\.(' + '|'.join([ft[1][ft[1].rfind('.') + 1:] for ft in filetypes]) + ')')
        self.names = [name for name in self.myzip.namelist() if len(file_type_matcher.findall(name.lower())) > 0 and \
                      os.path.basename(name) == name]
        self.myzip = ZipFile(zip_filename, 'r')

    def getFile(self, name):
        return self.myzip.extract(name, self.dir)

    def isOpened(self):
        #TODO: check names, what else
        return True

    def release(self):
        import shutil
        shutil.rmtree(self.dir)
        self.myzip.close()
