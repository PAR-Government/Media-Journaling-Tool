import unittest
import os
from maskgen import plugins, video_tools
from tests.test_support import TestSupport


def get_channel_data(source_data, codec_type):
    pos = 0
    for data in source_data:
        if data['codec_type'] == codec_type:
            return data,pos
        pos+=1

class CropSelectorTestCase(TestSupport):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_drop_then_add(self):
        filename= self.locateFile('tests/videos/sample1.mov')
        filename_output1 = os.path.join(os.path.dirname(os.path.abspath(filename)),'sample_out1a.avi')
        kwargs = {'Start Time':100,
                 'seconds to drop': 2,
                 'codec':'XVID',
                  'save histograms':'yes'}
        args,error = plugins.callPlugin('FlowDrivenVideoFrameDrop',
                            None,
                           filename,
                           filename_output1,
                           **kwargs)
        self.filesToKill.append(filename_output1)
        self.assertTrue(error is None)
        frames1 = int(get_channel_data(video_tools.getMeta(filename, show_streams=True)[0], 'video')[0]['nb_frames'])
        frames2 = int(
            get_channel_data(video_tools.getMeta(filename_output1, show_streams=True)[0], 'video')[0]['nb_frames'])
        diff = frames1-frames2
        self.assertTrue(diff>0)
        diff_time = int(args['End Time']) - int(args['Start Time'])
        self.assertEqual(diff, diff_time)
        filename_output2 = os.path.join(os.path.dirname(os.path.abspath(filename)), 'sample_out2a.avi')
        args['codec'] = 'XVID'
        print str(args)
        args, error = plugins.callPlugin('FlowDrivenVideoTimeWarp',
                                         None,
                                         filename_output1,
                                         filename_output2,
                                         **args)
        self.filesToKill.append(filename_output2)
        self.assertTrue(error is None)
        frames1 = int(get_channel_data(video_tools.getMeta(filename_output1, show_streams=True)[0], 'video')[0]['nb_frames'])
        frames2 = int(
            get_channel_data(video_tools.getMeta(filename_output2, show_streams=True)[0], 'video')[0]['nb_frames'])
        diff = frames2 - frames1
        self.assertTrue(diff > 0)
        diff_time = int(args['End Time']) - int(args['Start Time'])
        print str(args)
        self.assertEqual(diff, diff_time - 1)

    def tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
