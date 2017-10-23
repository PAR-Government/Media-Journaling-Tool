from maskgen import video_tools,tool_set
import unittest
import numpy as np
import cv2
import os


class TestVideoTools(unittest.TestCase):


    def _init_write_file(self, name, start_time, amount, fps):
        import math
        writer = tool_set.GrayBlockWriter(name, fps)
        mask_set = list()
        amount = int(amount)
        increment = 1000 / float(fps)
        for i in range(amount):
            mask = np.random.randint(255, size=(1090, 1920)).astype('uint8')
            mask_set.append(mask)
            writer.write(mask, start_time)
            start_time += increment
        writer.close()
        return writer.filename

    def test_meta(self):
        meta,frames = video_tools.getMeta('tests/videos/sample1.mov',show_streams=True)
        self.assertEqual('yuv444p',meta[0]['pix_fmt'])

    def test_before_dropping(self):
        import math
        import os
        import sys
        amount = 30
        fileOne = self._init_write_file('test_ts_bd1',2500,30,30)
        fileTwo = self._init_write_file('test_ts_bd2', 4100,27,30)
        sets= []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = ''
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = fileOne
        sets.append(change)
        change = dict()
        change['starttime'] = 4100
        change['startframe'] = 123
        change['endtime'] = 5000
        change['endframe'] = change['startframe'] + 27
        change['frames'] = int(27)
        change['rate'] = 30
        change['videosegment'] = fileTwo
        sets.append(change)
        result  = video_tools.dropFramesFromMask('00:00:03.000:0','00:00:04.000:0',sets)
        self.assertEqual(3, len(result))
        self.assertEqual(16,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(91, result[1]['endframe'])
        self.assertEqual(93, result[2]['startframe'])
        self.assertEqual(120, result[2]['endframe'])

        result = video_tools.dropFramesFromMask('00:00:02.100:0', '00:00:03.000:0',  sets)
        self.assertEqual(3, len(result))
        self.assertEqual(14, result[1]['frames'])
        self.assertEqual(64, result[1]['startframe'])
        self.assertEqual(78, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(123, result[2]['endframe'])

        result = video_tools.dropFramesFromMask('00:00:02.900:0', '00:00:03.100:0',  sets)
        self.assertEqual(4, len(result))
        self.assertEqual(13, result[1]['frames'])
        self.assertEqual(11, result[2]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(88, result[1]['endframe'])
        self.assertEqual(88, result[2]['startframe'])
        self.assertEqual(99, result[2]['endframe'])
        self.assertEqual(117, result[3]['startframe'])
        self.assertEqual(144, result[3]['endframe'])

        result = video_tools.dropFramesFromMask('00:00:02.900:0', '00:00:03.100:0',  sets, keepTime=True)
        self.assertEqual(4, len(result))
        self.assertEqual(13, result[1]['frames'])
        self.assertEqual(11, result[2]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(88, result[1]['endframe'])
        self.assertEqual(94, result[2]['startframe'])
        self.assertEqual(105, result[2]['endframe'])
        self.assertEqual(123, result[3]['startframe'])
        self.assertEqual(150, result[3]['endframe'])

        result = video_tools.dropFramesFromMask('00:00:00.000', '00:00:03.100:0',  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(11, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(12, result[0]['endframe'])
        self.assertEqual(30, result[1]['startframe'])
        self.assertEqual(57, result[1]['endframe'])

        result = video_tools.dropFramesFromMask('00:00:03.100:0',None ,  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        self.assertEqual(30, result[0]['endframe'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(94, result[1]['endframe'])

        result = video_tools.dropFramesFromMask('00:00:00.000', '00:00:03.100:0',  sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(11, result[0]['frames'])
        self.assertEqual(94, result[0]['startframe'])
        self.assertEqual(105, result[0]['endframe'])
        self.assertEqual(123, result[1]['startframe'])
        self.assertEqual(150, result[1]['endframe'])

        result = video_tools.dropFramesFromMask('00:00:03.100:0', None,  sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        self.assertEqual(30, result[0]['endframe'])
        self.assertEqual(19, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(94, result[1]['endframe'])


    def test_before_dropping_nomask(self):
        import math
        import os
        import sys
        amount = 30
        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] =  1000
        change['endframe'] = amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = ''
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = ''
        sets.append(change)
        change = dict()
        change['starttime'] = 4100
        change['startframe'] = 123
        change['endtime'] = 5000
        change['endframe'] = change['startframe'] +  27
        change['frames'] = int(27)
        change['rate'] = 30
        change['videosegment'] = ''
        sets.append(change)
        result  = video_tools.dropFramesWithoutMask('00:00:02.900:0','00:00:03.100:0',sets)
        self.assertEqual(4, len(result))
        self.assertEqual(12,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(87, result[1]['endframe'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(87, result[2]['startframe'])
        self.assertEqual(117, result[3]['startframe'])
        self.assertEqual(144, result[3]['endframe'])

        result = video_tools.dropFramesWithoutMask('00:00:02.100:0', '00:00:03.000:0',  sets)
        self.assertEqual(3, len(result))
        self.assertEqual(15, result[1]['frames'])
        self.assertEqual(63, result[1]['startframe'])
        self.assertEqual(78, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(123, result[2]['endframe'])

        result = video_tools.dropFramesWithoutMask('00:00:02.900:0', '00:00:03.100:0',  sets, keepTime=True)
        self.assertEqual(4, len(result))
        self.assertEqual(12,  result[1]['frames'])
        self.assertEqual(12,  result[2]['frames'])
        self.assertEqual(75,  result[1]['startframe'])
        self.assertEqual(87,  result[1]['endframe'])
        self.assertEqual(93,  result[2]['startframe'])
        self.assertEqual(105, result[2]['endframe'])
        self.assertEqual(123, result[3]['startframe'])
        self.assertEqual(150, result[3]['endframe'])

        result = video_tools.dropFramesWithoutMask('00:00:00.000', '00:00:03.100:0',  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(0,  result[0]['startframe'])
        self.assertEqual(12, result[0]['endframe'])
        self.assertEqual(30, result[1]['startframe'])
        self.assertEqual(57, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask('00:00:03.100:0',None ,  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        self.assertEqual(30, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask('00:00:00.000', '00:00:03.100:0',  sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(93, result[0]['startframe'])
        self.assertEqual(105, result[0]['endframe'])
        self.assertEqual(123, result[1]['startframe'])
        self.assertEqual(150, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask('00:00:03.100:0', None, sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        self.assertEqual(30, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])

    def test_after_dropping(self):
        import math
        import os
        import sys
        amount = 30
        fileOne = self._init_write_file('test_ts_ad1', 0,30,30)
        fileTwo = self._init_write_file('test_ts_ad1',2500,30,30)
        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = fileOne
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = int(30 * 2.5)
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = fileTwo
        sets.append(change)
        result = video_tools.insertFramesToMask('00:00:06.000:0', '00:00:07.000:0',  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(amount, result[1]['frames'])

        result = video_tools.insertFramesToMask('00:00:02.100:0', '00:00:03.000:0',  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[1]['frames'])
        self.assertEqual(102, result[1]['startframe'])

        result = video_tools.insertFramesToMask('00:00:02.700:0', '00:00:03.700:0',  sets)
        self.assertEqual(3, len(result))
        self.assertEqual(7, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(23, result[2]['frames'])
        self.assertEqual(112, result[2]['startframe'])
        self.assertEqual(135, result[2]['endframe'])

        result = video_tools.insertFramesToMask('00:00:00.000:0', '00:00:02.100:0',  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(30, result[1]['frames'])
        self.assertEqual(63, result[0]['startframe'])
        self.assertEqual(93, result[0]['endframe'])
        self.assertEqual(138, result[1]['startframe'])
        self.assertEqual(168, result[1]['endframe'])


    def test_after_dropping_nomask(self):
        import math
        import os
        import sys
        amount = 29
        fileOne = ''
        fileTwo = ''
        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = amount
        change['frames'] = amount
        change['rate'] = 29
        change['videosegment'] = fileOne
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = int(29 * 2.5)
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 29
        change['videosegment'] = fileTwo
        sets.append(change)
        result = video_tools.insertFramesWithoutMask('00:00:06.000:0', '00:00:07.000:0', sets)
        self.assertEqual(2, len(result))
        self.assertEqual(amount, result[1]['frames'])

        result = video_tools.insertFramesWithoutMask('00:00:02.100:0', '00:00:03.000:0',  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(29, result[1]['frames'])
        self.assertEqual(98, result[1]['startframe'])
        self.assertEqual(127, result[1]['endframe'])

        result = video_tools.insertFramesWithoutMask('00:00:02.700:0', '00:00:03.700:0', sets)
        self.assertEqual(3, len(result))
        self.assertEqual(6, result[1]['frames'])
        self.assertEqual(23, result[2]['frames'])

        result = video_tools.insertFramesWithoutMask('00:00:00.000:0', '00:00:02.100:0',  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(29, result[0]['frames'])
        self.assertEqual(29, result[1]['frames'])
        self.assertEqual(60, result[0]['startframe'])
        self.assertEqual(89, result[0]['endframe'])
        self.assertEqual(132, result[1]['startframe'])
        self.assertEqual(161, result[1]['endframe'])

    def test_resize(self):
        fileOne = self._init_write_file('test_td_rs', 0, 30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['videosegment'] = fileOne
        result = video_tools.resizeMask([change], (1000, 1720))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])


    def test_rotate(self):
        fileOne = self._init_write_file('test_td_rs', 0, 30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['videosegment'] = fileOne
        result = video_tools.rotateMask([change],-90, expectedDims=(1920,1090))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])


    def test_crop(self):
        fileOne = self._init_write_file('test_td_rs', 0, 30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['videosegment'] = fileOne
        result = video_tools.cropMask([change],(100,100,900,1120))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        result = video_tools.insertMask( [change], (100, 100, 900, 1120),(1090,1920))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])

if __name__ == '__main__':
    unittest.main()
