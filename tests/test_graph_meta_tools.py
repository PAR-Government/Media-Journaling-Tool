import unittest
from test_support import TestSupport
from maskgen import video_tools
from maskgen.graph_meta_tools import MetaDataExtractor, GraphProxy, get_meta_data_change_from_edge
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

    def test_Audio_to_Video(self):
        source = self.locateFile('tests/videos/sample1.mov')
        extractor = MetaDataExtractor(GraphProxy(source, 'b'))
        masks = [video_tools.create_segment(endframe= 2618367,
                                            rate= 44100,
                                            starttime=0.0,
                                            frames= 2618367,
                                            startframe=1,
                                            endtime=59373.424,
                                            type='audio')]
        newMasks = extractor.create_video_for_audio(source, masks=masks)
        self.assertTrue(len(newMasks) > len(masks))
        self.assertTrue(video_tools.get_start_frame_from_segment(newMasks[1]) == 1)
        self.assertTrue(video_tools.get_end_frame_from_segment(newMasks[1]) == 803)
        self.assertTrue(video_tools.get_rate_from_segment(newMasks[1]) == 28.25)
        self.assertTrue(video_tools.get_end_time_from_segment(newMasks[1]) == 59348.333)
        source = self.locateFile('tests/videos/Sample1_slow.mov')
        masks = [video_tools.create_segment(endframe= 441000,
                                            rate= 44100,
                                            starttime=1000.0,
                                            frames= 396901,
                                            startframe=44100,
                                            endtime=10000.0,
                                            type='audio')]
        newMasks = extractor.create_video_for_audio(source, masks=masks)
        self.assertTrue(len(newMasks) > len(masks))
        self.assertTrue(video_tools.get_rate_from_segment(newMasks[1]) == 10.0)
        self.assertTrue(video_tools.get_start_frame_from_segment(newMasks[1]) == 11)
        self.assertTrue(video_tools.get_end_frame_from_segment(newMasks[1]) == 100)

    def test_get_meta_data_change_from_edge(self):
        result = get_meta_data_change_from_edge({'metadatadiff': {'video': {
            'nb_frames': ('change',9,10),
            'r_frame_rate': ('change',29,30),
            'duration': ('change',10,11)
        }}})
        self.assertEqual(9,result[0])
        self.assertEqual(10000, result[1])
        self.assertEqual(10, result[2])
        self.assertEqual(11000, result[3])
        self.assertEqual(30, result[4])




    def testWarp(self):
        source = self.locateFile('tests/videos/sample1.mov')
        target = 'sample1_ffr_ex.mov'
        source_set = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator(source),
                                                          start_time='29', end_time='55')
        target_set = video_tools.getMaskSetForEntireVideoForTuples(video_tools.FileMetaDataLocator(target),
                                                                   start_time_tuple=(video_tools.get_start_time_from_segment(source_set[0]), 0),
                                                                   end_time_tuple=(video_tools.get_end_time_from_segment(source_set[0]), 0))
        print(source_set[0])
        extractor = MetaDataExtractor(GraphProxy(source,target))
        new_mask_set = extractor.warpMask(source_set, source, source)
        print(new_mask_set[0])
        self.assertTrue(video_tools.get_frames_from_segment(new_mask_set[0]) == video_tools.get_frames_from_segment(source_set[0]))
        self.assertTrue(video_tools.get_end_time_from_segment(new_mask_set[0]) == video_tools.get_end_time_from_segment(source_set[0]))
        self.assertTrue(video_tools.get_rate_from_segment(new_mask_set[0]) == video_tools.get_rate_from_segment(source_set[0]))
        self.assertTrue(video_tools.get_start_frame_from_segment(new_mask_set[0]) == video_tools.get_start_frame_from_segment(source_set[0]))
        self.assertTrue(video_tools.get_start_time_from_segment(new_mask_set[0]) == video_tools.get_start_time_from_segment(source_set[0]))
        self._add_mask_files_to_kill(source_set)
        new_mask_set = extractor.warpMask(source_set,  source, target)
        self.assertTrue(video_tools.get_frames_from_segment(new_mask_set[0]) == video_tools.get_frames_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_end_time_from_segment(new_mask_set[0]) == video_tools.get_end_time_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_rate_from_segment(new_mask_set[0]) == video_tools.get_rate_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_start_frame_from_segment(new_mask_set[0]) == video_tools.get_start_frame_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_start_time_from_segment(new_mask_set[0]) == video_tools.get_start_time_from_segment(target_set[0]))
        source_mask_set = extractor.warpMask(new_mask_set, source, target, inverse=True)
        self.assertTrue(abs(video_tools.get_frames_from_segment(source_mask_set[0]) - video_tools.get_frames_from_segment(source_set[0])) < 2)
        self.assertTrue(abs(video_tools.get_end_time_from_segment(source_mask_set[0]) - video_tools.get_end_time_from_segment(source_set[0])) < video_tools.get_error_from_segment(source_mask_set[0]) * 2)
        self.assertTrue(abs(video_tools.get_rate_from_segment(source_mask_set[0]) - video_tools.get_rate_from_segment(source_set[0])) < 0.1)
        self.assertTrue(abs(video_tools.get_start_frame_from_segment(source_mask_set[0]) - video_tools.get_start_frame_from_segment(source_set[0])) < 2)
        self.assertTrue(
            abs(video_tools.get_start_time_from_segment(source_mask_set[0]) - video_tools.get_start_time_from_segment(source_set[0])) < video_tools.get_error_from_segment(source_mask_set[0]) * 2)
        new_mask_set = extractor.warpMask(source_set, source, target, useFFMPEG=True)
        self.assertTrue(video_tools.get_frames_from_segment(new_mask_set[0]) == video_tools.get_frames_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_end_time_from_segment(new_mask_set[0]) == video_tools.get_end_time_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_rate_from_segment(new_mask_set[0]) == video_tools.get_rate_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_start_frame_from_segment(new_mask_set[0]) == video_tools.get_start_frame_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_start_time_from_segment(new_mask_set[0]) == video_tools.get_start_time_from_segment(target_set[0]))
        source_mask_set = extractor.warpMask(new_mask_set, source, target, inverse=True, useFFMPEG=True)
        self.assertTrue(abs(video_tools.get_frames_from_segment(source_mask_set[0]) - video_tools.get_frames_from_segment(source_set[0])) < 2)
        self.assertTrue(abs(video_tools.get_end_time_from_segment(source_mask_set[0]) - video_tools.get_end_time_from_segment(source_set[0])) < video_tools.get_error_from_segment(source_mask_set[0]) * 2)
        self.assertTrue(abs(video_tools.get_rate_from_segment(source_mask_set[0]) - video_tools.get_rate_from_segment(source_set[0])) < 0.1)
        self.assertTrue(abs(video_tools.get_start_frame_from_segment(source_mask_set[0]) - video_tools.get_start_frame_from_segment(source_set[0])) < 2)
        self.assertTrue(
            abs(video_tools.get_start_time_from_segment(source_mask_set[0]) - video_tools.get_start_time_from_segment(source_set[0])) < video_tools.get_error_from_segment(source_mask_set[0]) * 2)

        source_set = target_set
        source = target
        target = 'sample1_ffr_2_ex.mov'
        target_set = video_tools.getMaskSetForEntireVideoForTuples(video_tools.FileMetaDataLocator(target),
                                                                   start_time_tuple=(video_tools.get_start_time_from_segment(source_set[0]), 0),
                                                                   end_time_tuple=(video_tools.get_end_time_from_segment(source_set[0]), 0))
        new_mask_set = extractor.warpMask(new_mask_set, source, target)
        self.assertTrue(video_tools.get_frames_from_segment(new_mask_set[0]) == video_tools.get_frames_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_end_time_from_segment(new_mask_set[0]) == video_tools.get_end_time_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_rate_from_segment(new_mask_set[0]) == video_tools.get_rate_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_start_frame_from_segment(new_mask_set[0]) == video_tools.get_start_frame_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_start_time_from_segment(new_mask_set[0]) == video_tools.get_start_time_from_segment(target_set[0]))

if __name__ == '__main__':
    unittest.main()
