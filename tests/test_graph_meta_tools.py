import unittest
from test_support import TestSupport
from maskgen import video_tools
from maskgen.graph_meta_tools import MetaDataExtractor, GraphProxy, get_meta_data_change_from_edge
import os


class TestGraphMetaTools(TestSupport):

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
        self.assertEquals(803,video_tools.get_end_frame_from_segment(newMasks[1]))
        self.assertTrue(1352,int(video_tools.get_rate_from_segment(newMasks[1]) *100))
        self.assertTrue(5934833 ,int(video_tools.get_end_time_from_segment(newMasks[1])*100))
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




    def test_warp(self):
        source = self.locateFile('tests/videos/sample1.mov')
        target = 'sample1_ffr_ex.mov'
        source_set = video_tools.FileMetaDataLocator(source).getMaskSetForEntireVideo(
                                                          start_time='29', end_time='55')
        target_set = video_tools.FileMetaDataLocator(target).getMaskSetForEntireVideoForTuples(
                                                                   start_time_tuple=(video_tools.get_start_time_from_segment(source_set[0]), 0),
                                                                   end_time_tuple=(video_tools.get_end_time_from_segment(source_set[0]), 0))
        extractor = MetaDataExtractor(GraphProxy(source,target))
        new_mask_set = extractor.warpMask(source_set, source, source)
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
        target_set = video_tools.FileMetaDataLocator(target).getMaskSetForEntireVideoForTuples(
                                                                   start_time_tuple=(video_tools.get_start_time_from_segment(source_set[0]), 0),
                                                                   end_time_tuple=(video_tools.get_end_time_from_segment(source_set[0]), 0))
        new_mask_set = extractor.warpMask(source_set, source, target)
        self.assertTrue(video_tools.get_frames_from_segment(new_mask_set[0]) == video_tools.get_frames_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_end_time_from_segment(new_mask_set[0]) == video_tools.get_end_time_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_rate_from_segment(new_mask_set[0]) == video_tools.get_rate_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_start_frame_from_segment(new_mask_set[0]) == video_tools.get_start_frame_from_segment(target_set[0]))
        self.assertTrue(video_tools.get_start_time_from_segment(new_mask_set[0]) == video_tools.get_start_time_from_segment(target_set[0]))

    def create_masks(self,mask_set):
        from maskgen import tool_set
        import numpy as np

        for segment in mask_set:
            writer = tool_set.GrayBlockWriter('test_warp',video_tools.get_rate_from_segment(segment))
            for i in range(video_tools.get_frames_from_segment(segment)):
                f = i + video_tools.get_start_frame_from_segment(segment)
                writer.write(np.random.randint(0,1,(1000,1000),'uint8')*255,
                             (f-1)*video_tools.get_rate_from_segment(segment),
                             frame_number=f)
            writer.close()
            video_tools.update_segment(segment, videosegment=writer.filename)
            self.addFileToRemove(writer.filename)

    def read_masks(self, mask_set):
        from maskgen import tool_set
        r = []
        for segment in mask_set:
            reader = tool_set.GrayBlockReader(video_tools.get_file_from_segment(segment))
            r.append({'start_time':reader.current_frame_time(),
                      'start_frame':reader.current_frame(),
                      'frames': reader.length()})
        return r


    def test_warp(self):

        def run_warp(source, target,start_time, end_time):
            source_set = video_tools.FileMetaDataLocator(source).getMaskSetForEntireVideo(
                start_time=start_time, end_time=end_time)
            self.create_masks(source_set)
            extractor = MetaDataExtractor(GraphProxy(source, target))
            target_set = video_tools.FileMetaDataLocator(target).getMaskSetForEntireVideoForTuples(
                start_time_tuple=(video_tools.get_start_time_from_segment(source_set[0]), 0),
                end_time_tuple=(video_tools.get_end_time_from_segment(source_set[0]), 0))
            new_mask_set = extractor.warpMask(source_set, source, target)
            self.assertTrue(
                video_tools.get_frames_from_segment(new_mask_set[0]) == video_tools.get_frames_from_segment(
                    target_set[0]))
            self.assertTrue(
                video_tools.get_end_time_from_segment(new_mask_set[0]) == video_tools.get_end_time_from_segment(
                    target_set[0]))
            self.assertTrue(
                video_tools.get_rate_from_segment(new_mask_set[0]) == video_tools.get_rate_from_segment(target_set[0]))
            self.assertTrue(
                video_tools.get_start_frame_from_segment(new_mask_set[0]) == video_tools.get_start_frame_from_segment(
                    target_set[0]))
            self.assertTrue(
                video_tools.get_start_time_from_segment(new_mask_set[0]) == video_tools.get_start_time_from_segment(
                    target_set[0]))
            file_data = self.read_masks(new_mask_set)
            self.assertEqual(video_tools.get_frames_from_segment(new_mask_set[0]), file_data[0]['frames'])

        run_warp('sample1_ffr_2_ex.mov', 'sample1_ffr_ex.mov', '10', '24')

        run_warp('sample1_ffr_ex.mov', 'sample1_ffr_2_ex.mov', '10', '24')

        run_warp( self.locateFile('tests/videos/sample1.mov'), 'sample1_ffr_2_ex.mov','29','55')



        run_warp('sample1_ffr_2_ex.mov',  self.locateFile('tests/videos/sample1.mov'), '29', '55')





if __name__ == '__main__':
    unittest.main()
