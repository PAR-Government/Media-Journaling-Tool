import unittest
from tests.test_support import TestSupport
from mock import  Mock
from maskgen.masks.donor_rules import VideoDonor, AudioDonor, AllStreamDonor, AllAudioStreamDonor, \
    VideoDonorWithoutAudio, InterpolateDonor
from maskgen.video_tools import get_type_of_segment, get_start_time_from_segment, get_start_frame_from_segment, \
    get_end_time_from_segment, get_end_frame_from_segment



class TestDonorRules(TestSupport):

    def test_video_donor(self):
        graph = Mock()
        def lkup_preds(x):
            return {'b':['a'],'e':['d']}[x]
        def lkup_edge(x,y):
            return {'ab':{'op':'NoSelect'},'de':{'op':'SelectSomething','arguments': {'Start Time': 20, 'End Time':100}}}[x + y]
        graph.predecessors = lkup_preds
        graph.get_edge = lkup_edge
        graph.dir = '.'

        donor = VideoDonor(graph, 'e','f', 'x',(None,self.locateFile('tests/videos/sample1.mov')), (None,self.locateFile('tests/videos/sample1.mov')))
        args = donor.arguments()
        self.assertEqual(20,  args['Start Time']['defaultvalue'])
        self.assertEqual(100, args['End Time']['defaultvalue'])
        segments = donor.create(arguments={'include audio':'yes','Start Time':30,'End Time':150})
        for segment in segments:
            if get_type_of_segment(segment) == 'audio':
                self.assertEqual(115542,get_start_frame_from_segment(segment))
                self.assertEqual(509061, get_end_frame_from_segment(segment))
            else:
                self.assertEqual(30, get_start_frame_from_segment(segment))
                self.assertEqual(150, get_end_frame_from_segment(segment))
            self.assertEqual(2620.0, get_start_time_from_segment(segment))
            self.assertEqual(11543, int(get_end_time_from_segment(segment)))


        donor = VideoDonor(graph, 'b','c','x', (None,self.locateFile('tests/videos/sample1.mov')), (None,self.locateFile('tests/videos/sample1.mov')))
        args = donor.arguments()
        self.assertEqual(1,  args['Start Time']['defaultvalue'])
        self.assertEqual(0, args['End Time']['defaultvalue'])
        segments = donor.create(arguments={'include audio':'yes','Start Time':30,'End Time':150})
        for segment in segments:
            if get_type_of_segment(segment) == 'audio':
                self.assertEqual(115542,get_start_frame_from_segment(segment))
                self.assertEqual(509061, get_end_frame_from_segment(segment))
            else:
                self.assertEqual(30, get_start_frame_from_segment(segment))
                self.assertEqual(150, get_end_frame_from_segment(segment))
            self.assertEqual(2620.0, get_start_time_from_segment(segment))
            self.assertEqual(11543, int(get_end_time_from_segment(segment)))

        segments = donor.create(arguments={'include audio': 'no', 'Start Time': 30, 'End Time': 150})
        self.assertEqual(0,len([segment for segment in segments if get_type_of_segment(segment) == 'audio']))

        donor = VideoDonorWithoutAudio(graph, 'b','c', 'x', (None,self.locateFile('tests/videos/sample1.mov')),
                                       (None,self.locateFile('tests/videos/sample1.mov')))
        self.assertTrue('include audio' not in donor.arguments())


    def test_audio_donor(self):
        graph = Mock()

        def lkup_preds(x):
            return {'b': ['a'], 'e': ['d']}[x]

        def lkup_edge(x, y):
            return \
            {'ab': {'op': 'NoSelect'}, 'de': {'op': 'SelectSomething', 'arguments': {'Start Time': 20, 'End Time': 100}}}[
                x + y]

        graph.predecessors = lkup_preds
        graph.get_edge = lkup_edge
        graph.dir = '.'

        donor = AudioDonor(graph,  'e', 'f', 'x', (None, self.locateFile('tests/videos/sample1.mov')),
                           (None, self.locateFile('tests/videos/sample1.mov')))
        args = donor.arguments()
        self.assertEqual("00:00:00.000000", args['Start Time']['defaultvalue'])
        self.assertEqual("00:00:00.000000", args['End Time']['defaultvalue'])
        segments = donor.create(arguments={'Start Time': "00:00:01.11", 'End Time': "00:00:01.32"})
        for segment in segments:
            self.assertEqual(48951, get_start_frame_from_segment(segment))
            self.assertEqual(58212, get_end_frame_from_segment(segment))
            self.assertAlmostEqual(1109.97, get_start_time_from_segment(segment),places=1)
            self.assertEqual(1320.0, int(get_end_time_from_segment(segment)))

        donor = AllStreamDonor(graph, 'e', 'f', 'y', (None, self.locateFile('tests/videos/sample1.mov')),
                           (None, self.locateFile('tests/videos/sample1.mov')))
        args = donor.arguments()
        self.assertEqual(0,len(args))
        segments = donor.create(arguments={})
        types = set()
        for segment in segments:
            types.add(get_type_of_segment(segment))
            if get_type_of_segment(segment) == 'audio':
                self.assertEqual(1, get_start_frame_from_segment(segment))
                self.assertEqual(2617262, get_end_frame_from_segment(segment))
                self.assertAlmostEqual(0, get_start_time_from_segment(segment), places=1)
                self.assertAlmostEqual(59348, int(get_end_time_from_segment(segment)))
            else:
                self.assertEqual(1, get_start_frame_from_segment(segment))
                self.assertEqual(803, get_end_frame_from_segment(segment))
                self.assertAlmostEqual(0, get_start_time_from_segment(segment), places=1)
                self.assertAlmostEqual(59348, int(get_end_time_from_segment(segment)))
        self.assertEqual(2,len(types))

        donor = AllAudioStreamDonor(graph, 'e', 'f', 'y', (None, self.locateFile('tests/videos/sample1.mov')),
                           (None, self.locateFile('tests/videos/sample1.mov')))
        self.assertEqual(0, len(donor.arguments()))
        self.assertEqual(['audio'],donor.media_types())


    def test_image_donor(self):
        import numpy as np
        from maskgen.image_wrap import ImageWrapper
        graph = Mock()

        def lkup_preds(x):
            return {'b': ['a'], 'e': ['d']}[x]

        def lkup_edge(x, y):
            return \
            {'ab': {'op': 'NoSelect'}, 'de': {'op': 'SelectRegion'}}[
                x + y]

        withoutalpha = ImageWrapper(np.zeros((400, 400, 3), dtype=np.uint8))
        withAlpha = ImageWrapper(np.zeros((400, 400, 4), dtype=np.uint8))
        mask = ImageWrapper(np.ones((400, 400),dtype = np.uint8)*255)
        mask.image_array[0:30, 0:30] = 0
        withAlpha.image_array[0:30, 0:30, 3] = 255

        graph.predecessors = lkup_preds
        graph.get_edge = lkup_edge
        graph.dir = '.'
        graph.get_edge_image = Mock(return_value=mask)

        donor = InterpolateDonor(graph, 'e', 'f', 'x', (withoutalpha, self.locateFile('tests/videos/sample1.mov')),
                           (withAlpha, self.locateFile('tests/videos/sample1.mov')))
        mask = donor.create(arguments={})
        self.assertTrue(np.all(mask.image_array[0:30,0:30] == 255))
        self.assertEquals(900,np.sum((mask.image_array/255)))

        donor = InterpolateDonor(graph, 'b', 'c', 'x', (withoutalpha, self.locateFile('tests/videos/sample1.mov')),
                                 (withAlpha, self.locateFile('tests/videos/sample1.mov')))
        mask = donor.create(arguments={})
        self.assertIsNone(mask)

        donor = InterpolateDonor(graph, 'b', 'c', 'x', (withAlpha, self.locateFile('tests/videos/sample1.mov')),
                                 (withAlpha, self.locateFile('tests/videos/sample1.mov')))
        mask = donor.create(arguments={})
        self.assertTrue(np.all(mask.image_array[0:30, 0:30] == 0))
        self.assertEquals(159100, np.sum((mask.image_array / 255)))


if __name__ == '__main__':
    unittest.main()
