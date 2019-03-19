# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
from maskgen import zip_tools
import unittest
from test_support import TestSupport
import sys,os


class TestPositions(zip_tools.Positions):
    def __init__(self,positions=[], fps=48000,duration=500.0):
        zip_tools.Positions.__init__(self, positions, fps=fps)
        self.duration = duration

    def _get_duration(self, position_file):
        return self.duration

class TestZipTool(TestSupport):

    @staticmethod
    def to_frame(frame_time, fps=48000):
        return int(frame_time * fps/1000.0) + 1

    def test_sub_positions(self):
        p = zip_tools.Positions([(1000, TestZipTool.to_frame(1000), 'foo1.wav'),
                   (5000, TestZipTool.to_frame(5000), 'foo2.wav'),
                   (10000, TestZipTool.to_frame(10000), 'foo3.wav')
                  ])
        subs = p.sub_positions(1500,11000)
        self.assertTrue(subs.size() == 3)
        subs = p.sub_positions(6000, 11000)
        self.assertTrue(subs.size() == 2)
        subs = p.sub_positions(1500, 9000)
        self.assertTrue(subs.size() == 2)
        subs = p.sub_positions(6000, 9000)
        self.assertTrue(subs.size()== 1)
        subs = p.sub_positions(6000, 9000)
        self.assertTrue(subs.size() == 1)


    def test_read_positions(self):
        with open('positions.csv','w') as fp:
            fp.writelines(['00:00:01.0000000,foo1.wav\n','00:00:05.0000000,foo3.wav\n','00:00:10.0000000,foo3.wav\n'])
        p1 = zip_tools.Positions.read('positions.csv')
        p2 = zip_tools.Positions([(1000, TestZipTool.to_frame(1000), 'foo1.wav'),
                                 (5000, TestZipTool.to_frame(5000), 'foo2.wav'),
                                 (10000, TestZipTool.to_frame(10000), 'foo3.wav')
                                 ])
        for r in range(p1.size()):
            self.assertTrue(p1.positions[0] == p2.positions[0])
        os.remove('positions.csv')


    def test_get_segments(self):
        p2 = TestPositions([(1000, TestZipTool.to_frame(1000), 'foo1.wav'),
                                  (5000, TestZipTool.to_frame(5000), 'foo2.wav'),
                                  (10000, TestZipTool.to_frame(10000), 'foo3.wav')
                                  ])
        segments = p2.get_segments(6000, 11000)
        self.assertEquals(segments[0][2],6500.0)
        self.assertEquals(segments[1][2], 10500.0)

        p2 = TestPositions([(1000, TestZipTool.to_frame(1000), 'foo1.wav'),
                            (5000, TestZipTool.to_frame(5000), 'foo2.wav'),
                            (10000, TestZipTool.to_frame(10000), 'foo3.wav')
                            ],duration=8000)
        segments = p2.get_segments(6000, 11000)
        self.assertEquals(int(segments[0][2]*100), 999999)
        self.assertEquals(segments[1][2], 18000.0)

    def test_audio_without_positions(self):
        audio = zip_tools.AudioPositions(self.locateFile('zips/test.wav.zip'),fps=44100)
        self.assertEqual([0,893968,1783292],[int(p[0]*100) for p in audio.positions])
        self.assertEqual(['output-audio-1.wav','output-audio-2.wav','output-audio-3.wav'],[p[2] for p in audio.positions])
        self.assertFalse(audio.validate_duration(self.locateFile('zips/output-audio-3.wav')))
        self.assertTrue(audio.validate_duration(self.locateFile('zips/output-audio-3.wav'), 17832.92))

    def test_audio_with_positions(self):
        with open('positions.csv', 'w') as fp:
            fp.writelines(['00:00:00.0000000,output-audio-1.wav\n', '00:00:08.5000000,output-audio-2.wav\n', '00:00:16.0000000,output-audio-3.wav\n'])
        audio = zip_tools.AudioPositions(self.locateFile('zips/test.wav.zip'),
                                         position_file_name='positions.csv',
                                         fps=44100)
        self.assertEqual([0, 850000, 1600000], [int(p[0] * 100) for p in audio.positions])
        self.assertEqual(['output-audio-1.wav', 'output-audio-2.wav', 'output-audio-3.wav'],
                         [p[2] for p in audio.positions])
        os.remove('positions.csv')

    def test_audio_with_positions_and_bad_files(self):
        with open('positions.csv', 'w') as fp:
            fp.writelines(['00:00:00.0000000,foo-audio-1.wav\n', '00:00:08.5000000,foo-audio-2.wav\n', '00:00:16.0000000,output-audio-3.wav\n'])
        with self.assertRaises(Exception) as context:
             zip_tools.AudioPositions(self.locateFile('zips/test.wav.zip'),
                                             position_file_name='positions.csv')

