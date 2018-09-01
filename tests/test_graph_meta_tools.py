from maskgen import graph_rules
import unittest
from maskgen.scenario_model import loadProject
from test_support import TestSupport
from mock import MagicMock, Mock
from maskgen.validation.core import Severity
from maskgen import video_tools
from maskgen.graph_meta_tools import MetaDataExtractor, GraphProxy
import os

class TestMetaExtractor(TestSupport):

    def __init__(self, stuff):
        TestSupport.__init__(self,stuff)
        self.filesToKill = []

    def setUp(self):
        source = self.locateFile('tests/videos/sample1.mov')
        target = 'sample1_ffr_ex.mov'
        os.system('ffmpeg -y -i "{}"  -r 10/1  "{}"'.format(source, target))
        self.addFileToRemove(target)
        source = self.locateFile('tests/videos/sample1.mov')
        target = 'sample1_ffr_2_ex.mov'
        os.system('ffmpeg -y -i "{}"  -r 8/1  "{}"'.format(source, target))
        self.addFileToRemove(target)

    def tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

    def _add_mask_files_to_kill(self, segments):
        for segment in segments:
            if 'videosegment' in segment:
                self.filesToKill.append(segment['videosegment'])

    def testCache(self):
        from maskgen.scenario_model import VideoAddTool
        tool = VideoAddTool()
        source = self.locateFile('tests/videos/sample1.mov')
        target = 'sample1_ffr_ex.mov'
        extractor = MetaDataExtractor(GraphProxy(source, target, source_node=tool.getAdditionalMetaData(source),
                                                 target_node={'media':[{'codec_type':'video','height':1000}]}))
        meta = extractor.getVideoMeta(source, show_streams=True)
        self.assertEqual('803', meta[0][0]['nb_frames'])
        meta = extractor.getVideoMeta(target, show_streams=True)
        self.assertEqual(1000, meta[0][0]['height'])

    def testWarp(self):
        source = self.locateFile('tests/videos/sample1.mov')
        target = 'sample1_ffr_ex.mov'
        source_set = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator(source),
                                                          start_time='29', end_time='55')
        target_set = video_tools.getMaskSetForEntireVideoForTuples(video_tools.FileMetaDataLocator(target),
                                                                   start_time_tuple=(source_set[0]['starttime'], 0),
                                                                   end_time_tuple=(source_set[0]['endtime'], 0))
        print(source_set[0])
        extractor = MetaDataExtractor(GraphProxy(source,target))
        new_mask_set = extractor.warpMask(source_set, source, source)
        print(new_mask_set[0])
        self.assertTrue(new_mask_set[0]['frames'] == source_set[0]['frames'])
        self.assertTrue(new_mask_set[0]['endtime'] == source_set[0]['endtime'])
        self.assertTrue(new_mask_set[0]['rate'] == source_set[0]['rate'])
        self.assertTrue(new_mask_set[0]['startframe'] == source_set[0]['startframe'])
        self.assertTrue(new_mask_set[0]['starttime'] == source_set[0]['starttime'])
        self._add_mask_files_to_kill(source_set)
        new_mask_set = extractor.warpMask(source_set,  source, target)
        self.assertTrue(new_mask_set[0]['frames'] == target_set[0]['frames'])
        self.assertTrue(new_mask_set[0]['endtime'] == target_set[0]['endtime'])
        self.assertTrue(new_mask_set[0]['rate'] == target_set[0]['rate'])
        self.assertTrue(new_mask_set[0]['startframe'] == target_set[0]['startframe'])
        self.assertTrue(new_mask_set[0]['starttime'] == target_set[0]['starttime'])
        source_mask_set = extractor.warpMask(new_mask_set, source, target, inverse=True)
        self.assertTrue(abs(source_mask_set[0]['frames'] - source_set[0]['frames']) < 2)
        self.assertTrue(abs(source_mask_set[0]['endtime'] - source_set[0]['endtime']) < source_mask_set[0]['error'] * 2)
        self.assertTrue(abs(source_mask_set[0]['rate'] - source_set[0]['rate']) < 0.1)
        self.assertTrue(abs(source_mask_set[0]['startframe'] - source_set[0]['startframe']) < 2)
        self.assertTrue(
            abs(source_mask_set[0]['starttime'] - source_set[0]['starttime']) < source_mask_set[0]['error'] * 2)
        new_mask_set = extractor.warpMask(source_set, source, target, useFFMPEG=True)
        self.assertTrue(new_mask_set[0]['frames'] == target_set[0]['frames'])
        self.assertTrue(new_mask_set[0]['endtime'] == target_set[0]['endtime'])
        self.assertTrue(new_mask_set[0]['rate'] == target_set[0]['rate'])
        self.assertTrue(new_mask_set[0]['startframe'] == target_set[0]['startframe'])
        self.assertTrue(new_mask_set[0]['starttime'] == target_set[0]['starttime'])
        source_mask_set = extractor.warpMask(new_mask_set, source, target, inverse=True, useFFMPEG=True)
        self.assertTrue(abs(source_mask_set[0]['frames'] - source_set[0]['frames']) < 2)
        self.assertTrue(abs(source_mask_set[0]['endtime'] - source_set[0]['endtime']) < source_mask_set[0]['error'] * 2)
        self.assertTrue(abs(source_mask_set[0]['rate'] - source_set[0]['rate']) < 0.1)
        self.assertTrue(abs(source_mask_set[0]['startframe'] - source_set[0]['startframe']) < 2)
        self.assertTrue(
            abs(source_mask_set[0]['starttime'] - source_set[0]['starttime']) < source_mask_set[0]['error'] * 2)

        source_set = target_set
        source = target
        target = 'sample1_ffr_2_ex.mov'
        target_set = video_tools.getMaskSetForEntireVideoForTuples(video_tools.FileMetaDataLocator(target),
                                                                   start_time_tuple=(source_set[0]['starttime'], 0),
                                                                   end_time_tuple=(source_set[0]['endtime'], 0))
        new_mask_set = extractor.warpMask(new_mask_set, source, target)
        self.assertTrue(new_mask_set[0]['frames'] == target_set[0]['frames'])
        self.assertTrue(new_mask_set[0]['endtime'] == target_set[0]['endtime'])
        self.assertTrue(new_mask_set[0]['rate'] == target_set[0]['rate'])
        self.assertTrue(new_mask_set[0]['startframe'] == target_set[0]['startframe'])
        self.assertTrue(new_mask_set[0]['starttime'] == target_set[0]['starttime'])

if __name__ == '__main__':
    unittest.main()
