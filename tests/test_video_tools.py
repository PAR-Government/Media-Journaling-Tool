from maskgen import video_tools,tool_set
import unittest
import numpy as np
import cv2
import os


def cropForTest(frame,no):
    return frame[100:-100,100:-100,:]

def rotateForTest(frame,no):
    return np.rotate(frame,-1)

def noiseForTest(frame,no):
    if no < 20 or no > 80:
        return frame
    result =  np.round(np.random.normal(0, 2, frame.shape))
    return frame+result.astype('uint8')

def sameForTest(frame,no):
    return frame

def addForTest(frame,no):
    if no != 20 :
        return frame
    return[ frame if i==0 else np.random.randint(255, size=(1090, 1920, 3)).astype('uint8') for i in range(20)]

def addNoise(frames,no):
    import random
    import struct
    import ctypes
    b = ctypes.create_string_buffer(len(frames))
    buffer_position = 0
    for i in range(0,len(frames),2):
        value = struct.unpack('h',frames[i:i+2])[0]
        position = no+buffer_position
        if (position >= 24 and position <= 64) or (position >= 192 and position <= 240 ):
            value = random.randint(-32767, 32767)
        struct.pack_into('h', b, buffer_position,value)
        buffer_position+=2
    return b

def sampleFrames(frames,no):
    import struct
    import ctypes
    if no < 1024:
        b = ctypes.create_string_buffer(192-24)
    else:
        return None
    buffer_position = 0
    read_position = 0
    for i in range(0,len(frames),2):
        value = struct.unpack('h',frames[i:i+2])[0]
        position = no+read_position
        read_position += 2
        if position < 24 or position >= 192:
            continue
        struct.pack_into('h', b, buffer_position,value)
        buffer_position+=2
    return b

def singleChannelSample(filename,outfilname,skip=0):
    import wave
    fone = wave.open(filename, 'rb')
    countone = fone.getnframes()
    ftwo = wave.open(outfilname, 'wb')
    ftwo.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
    onechannels = ftwo.getnchannels()
    onewidth = ftwo.getsampwidth()
    toRead = min([1024,countone])
    framesone = fone.readframes(toRead)
    ftwo.writeframes(framesone[24+skip:192-2+skip:2])
    fone.close()
    ftwo.close()


def augmentAudio(filename,outfilname,augmentFunc):
    import wave
    fone = wave.open(filename, 'rb')
    countone = fone.getnframes()
    onechannels = fone.getnchannels()
    onewidth = fone.getsampwidth()
    ftwo = wave.open(outfilname, 'wb')
    ftwo.setparams(fone.getparams())
    position = 0
    while True:
        toRead = min([1024,countone])
        countone -= toRead
        framesone = fone.readframes(toRead)
        result = augmentFunc(framesone, position)
        if result is None:
            break
        ftwo.writeframes(result)
        position += toRead
        if countone <= 0:
            break
    fone.close()
    ftwo.close()

class TestVideoTools(unittest.TestCase):
    filesToKill = []

    def _init_write_file(self, name, start_time, start_position, amount, fps,mask_set=None):
        writer = tool_set.GrayBlockWriter(name, fps)
        amount = int(amount)
        increment = 1000 / float(fps)
        count = start_position
        for i in range(amount):
            mask = np.random.randint(255, size=(1090, 1920)).astype('uint8')
            if mask_set is not None:
                mask_set.append(mask)
            writer.write(mask, start_time, count)
            start_time += increment
            count += 1
        writer.close()
        self.filesToKill.append(writer.filename)
        return writer.filename

    def _init_write_video_file(self, name, alter_funcs):
        try:
            writer_main  = tool_set.GrayFrameWriter(name,30/1.0, preferences={'vid_suffix':'avi','vid_codec':'raw'})
            rate = 1/30.0
            count = 0
            counters_for_all = [0 for i in alter_funcs]
            writers = [ tool_set.GrayFrameWriter(name+str(func).split()[1],30/1.0,preferences={'vid_suffix':'avi','vid_codec':'raw'}) for func in alter_funcs]
            for i in range(100):
                mask = np.random.randint(255, size=(1090, 1920,3)).astype('uint8')
                writer_main.write(mask, count*rate)
                nextcounts = []
                for writer,func,counter in zip(writers,alter_funcs,counters_for_all):
                    result = func(mask, i + 1)
                    if type(result) == list:
                        for item in result:
                            writer.write(item, count * rate)
                        nextcounts.append(counter + len(result))
                    else:
                        writer.write(result,count*rate )
                        nextcounts.append(counter+1)
                counters_for_all=nextcounts
                count += 1
        except Exception as ex:
            print ex
        finally:
            writer_main.close()
            for writer in writers:
                writer.close()
        self.filesToKill.append(writer.filename)
        filenames = self.filesToKill
        self.filesToKill.extend(filenames)
        return writer_main.filename, filenames

    """
    def test_meta(self):
        meta,frames = video_tools.getMeta('tests/videos/sample1.mov',show_streams=True)
        self.assertEqual('yuv420p',meta[0]['pix_fmt'])

    def test_frame_binding(self):
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov')
        self.assertEqual(0.0, result[0]['starttime'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(803,result[0]['frames'])
        self.assertEqual(803.0, result[0]['endframe'])
        self.assertEqual(59350.0, result[0]['endtime'])
        self.assertEqual('video', result[0]['type'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov',start_time='00:00:02.01')
        self.assertEqual(1982.0, round(result[0]['starttime']))
        self.assertEqual(24, result[0]['startframe'])
        self.assertEqual(803-24+1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov', start_time='00:00:02.01:02')
        self.assertEqual(2195.0, round(result[0]['starttime']))
        self.assertEqual(26, result[0]['startframe'])
        self.assertEqual(803 - 26 + 1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov', start_time='00:00:02.01',end_time='00:00:04')
        self.assertEqual(1982.0, round(result[0]['starttime']))
        self.assertEqual(24, result[0]['startframe'])
        self.assertEqual(3965.0, round(result[0]['endtime']))
        self.assertEqual(48, result[0]['endframe'])
        self.assertEqual(48 - 24 + 1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov',
                                                      media_types=['audio'])
        self.assertEqual(0.0, result[0]['starttime'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(2563, result[0]['frames'])
        self.assertEqual(2563.0, result[0]['endframe'])
        self.assertEqual(59348.0, round(result[0]['endtime']))
        self.assertEqual('audio', result[0]['type'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov', start_time='00:00:02.01',
                                                      end_time='00:00:04',
                                                      media_types=['audio'])
        self.assertEqual(2009.0, round(result[0]['starttime']))
        self.assertEqual(89, result[0]['startframe'])
        self.assertEqual(3983.0, round(result[0]['endtime']))
        self.assertEqual(174, result[0]['endframe'])
        self.assertEqual(174 - 89 + 1, result[0]['frames'])

    def test_before_dropping(self):

        amount = 30
        fileOne = self._init_write_file('test_ts_bd1',2500,75,30,30)
        fileTwo = self._init_write_file('test_ts_bd2', 4100,123,27,30)
        sets= []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 1000
        change['endframe'] = 31
        change['frames'] = 30
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = fileOne
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 4100
        change['startframe'] = 123
        change['endtime'] = 5000
        change['endframe'] = change['startframe'] + 27
        change['frames'] = int(27)
        change['rate'] = 30
        change['videosegment'] = fileTwo
        change['type'] = 'video'
        sets.append(change)

        result  = video_tools.dropFramesFromMask([{
            'startframe':90,
            'starttime':3000,
            'endframe':117,
            'endtime': 4000
        }],sets)
        self.assertEqual(3, len(result))
        self.assertEqual(15,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(90, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(123, result[2]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        }],sets)
        self.assertEqual(3, len(result))
        self.assertEqual(15, result[1]['frames'])
        self.assertEqual(63, result[1]['startframe'])
        self.assertEqual(78, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(123, result[2]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }],sets)

        self.assertEqual(4, len(result))
        self.assertEqual(12,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(87, result[1]['endframe'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(87, result[2]['startframe'])
        self.assertEqual(99, result[2]['endframe'])
        self.assertEqual(117, result[3]['startframe'])
        self.assertEqual(144, result[3]['endframe'])


        result = video_tools.dropFramesFromMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }], sets,keepTime=True)
        self.assertEqual(4, len(result))
        self.assertEqual(12, result[1]['frames'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(87, result[1]['endframe'])
        self.assertEqual(93, result[2]['startframe'])
        self.assertEqual(105, result[2]['endframe'])
        self.assertEqual(123, result[3]['startframe'])
        self.assertEqual(150, result[3]['endframe'])
        self.assertEqual(4, len(result))

        result = video_tools.dropFramesFromMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(13, result[0]['endframe'])
        self.assertEqual(31, result[1]['startframe'])
        self.assertEqual(58, result[1]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 93,
            'starttime': 3100
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(31, result[0]['endframe'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }], sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(93, result[0]['startframe'])
        self.assertEqual(105, result[0]['endframe'])
        self.assertEqual(123, result[1]['startframe'])
        self.assertEqual(150, result[1]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 93,
            'starttime': 3100,
        }], sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(31, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])



    def test_before_dropping_nomask(self):
        amount = 30
        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 1000
        change['endframe'] = 31
        change['frames'] = 30
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 4100
        change['startframe'] = 123
        change['endtime'] = 5000
        change['endframe'] = change['startframe'] + 27
        change['frames'] = int(27)
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        sets.append(change)
        result  = video_tools.dropFramesWithoutMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }],sets)
        self.assertEqual(4, len(result))
        self.assertEqual(12,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(87, result[1]['endframe'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(87, result[2]['startframe'])
        self.assertEqual(99, result[2]['endframe'])
        self.assertEqual(117, result[3]['startframe'])
        self.assertEqual(144, result[3]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        }],  sets)
        self.assertEqual(3, len(result))
        self.assertEqual(15, result[1]['frames'])
        self.assertEqual(63, result[1]['startframe'])
        self.assertEqual(78, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(123, result[2]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }],  sets, keepTime=True)
        self.assertEqual(4, len(result))
        self.assertEqual(12,  result[1]['frames'])
        self.assertEqual(12,  result[2]['frames'])
        self.assertEqual(75,  result[1]['startframe'])
        self.assertEqual(87,  result[1]['endframe'])
        self.assertEqual(93,  result[2]['startframe'])
        self.assertEqual(105, result[2]['endframe'])
        self.assertEqual(123, result[3]['startframe'])
        self.assertEqual(150, result[3]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }],  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(1,  result[0]['startframe'])
        self.assertEqual(13, result[0]['endframe'])
        self.assertEqual(31, result[1]['startframe'])
        self.assertEqual(58, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 93,
            'starttime': 3100
        }] , sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(31, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }],  sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(93, result[0]['startframe'])
        self.assertEqual(105, result[0]['endframe'])
        self.assertEqual(123, result[1]['startframe'])
        self.assertEqual(150, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 93,
            'starttime': 3100
        }], sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(31, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])

    def after_general_all(self, sets, func):
        result = func(
            [{
                'startframe': 180,
                'starttime': 6000,
                'endframe': 210,
                'endtime': 7000
            }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[1]['frames'])

        result = func([{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[1]['frames'])
        self.assertEqual(102, result[1]['startframe'])

        result = func([{
            'startframe': 81,
            'starttime': 2700,
            'endframe': 111,
            'endtime': 3700
        }], sets)
        self.assertEqual(3, len(result))
        self.assertEqual(6, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(24, result[2]['frames'])
        self.assertEqual(111, result[2]['startframe'])
        self.assertEqual(135, result[2]['endframe'])

        result = func([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 63,
            'endtime': 2100
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(30, result[1]['frames'])
        self.assertEqual(63, result[0]['startframe'])
        self.assertEqual(93, result[0]['endframe'])
        self.assertEqual(137, result[1]['startframe'])
        self.assertEqual(167, result[1]['endframe'])


    def test_after_dropping(self):
        amount = 30
        fileOne = self._init_write_file('test_ts_bd1', 0, 1, 30, 30)
        fileTwo = self._init_write_file('test_ts_bd2', 2500, 75, 30, 30)
        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 1000
        change['endframe'] = amount + 1
        change['frames'] = amount
        change['rate'] = 30
        change['type'] = 'video'
        change['videosegment'] = fileOne
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 30
        change['type'] = 'video'
        change['videosegment'] = fileTwo
        sets.append(change)
        self.after_general_all(sets,video_tools.insertFramesToMask)
        self.after_general_all(sets, video_tools.insertFramesWithoutMask)

    def test_resize(self):
        fileOne = self._init_write_file('test_td_rs', 0,1, 30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['type'] = 'video'
        change['videosegment'] = fileOne
        result = video_tools.resizeMask([change], (1000, 1720))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])


    def test_rotate(self):
        fileOne = self._init_write_file('test_td_rs', 0, 1,30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['type'] = 'video'
        change['videosegment'] = fileOne
        result = video_tools.rotateMask(-90,[change],expectedDims=(1920,1090))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])

    def test_crop(self):
        fileOne = self._init_write_file('test_td_rs', 0,1, 30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['type'] = 'video'
        change['videosegment'] = fileOne
        result = video_tools.cropMask([change],(100,100,900,1120))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        result = video_tools.insertMask( [change], (100, 100, 900, 1120),(1090,1920))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])



    def test_invertVideoMasks(self):
        start_set = []
        fileOne = self._init_write_file('test_iv_rs', 0, 1, 30, 30,mask_set=start_set)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['type'] = 'video'
        change['videosegment'] = fileOne
        result = video_tools.invertVideoMasks([change], 'x','y')
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        reader = tool_set.GrayBlockReader(result[0]['videosegment'])
        mask = reader.read()
        self.assertEqual(2,reader.current_frame())
        self.assertEqual(33, reader.current_frame_time())
        self.assertTrue(np.all(255-mask == start_set[0]))
        reader.close()


    def test_all_mods(self):
        mod_functions = [sameForTest,cropForTest,noiseForTest,addForTest]
        fileOne,modFiles = 'test_td_rs_mask_0.0.avi',['test_td_rssameForTest_mask_0.0.avi',
                                                      'test_td_rscropForTest_mask_0.0.avi',
                                                      'test_td_rsnoiseForTest_mask_0.0.avi',
                                                      'test_td_rsaddForTest_mask_0.0.avi']
        #fileOne,modFiles = self._init_write_video_file('test_td_rs',mod_functions)
        analysis = {}
        result_same, errors = video_tools.formMaskDiff(fileOne,
                                                         modFiles[0],
                                                         modFiles[0],
                                                         'AddNoise',
                                                         startSegment=None,
                                                         endSegment=None,
                                                         analysis=analysis,
                                                         alternateFunction=video_tools.detectCompare,
                                                         arguments={})
        self.assertEqual(0, len(result_same))
        analysis = {}
        result_add, errors = video_tools.formMaskDiff(fileOne,
                                                         modFiles[3],
                                                         modFiles[3],
                                                         'PasteFrames',
                                                         startSegment=None,
                                                         endSegment=None,
                                                         analysis=analysis,
                                                         alternateFunction=video_tools.pasteCompare,
                                                         arguments={})
        self.assertEqual(1, len(result_add))
        self.assertEqual(21,result_add[0]['startframe'])
        self.assertEqual(40, result_add[0]['endframe'])
        result_crop,errors = video_tools.formMaskDiff(fileOne,
                                 modFiles[1],
                                 modFiles[1],
                                 'TransformCrop',
                                 startSegment=None,
                                 endSegment=None,
                                 analysis=analysis,
                                 alternateFunction=video_tools.cropCompare,
                                 arguments={})
        self.assertEqual(1, len(result_crop))
        self.assertEqual(100, result_crop[0]['frames'])
        self.assertEqual(1, result_crop[0]['startframe'])
        self.assertTrue(analysis['location'].find('100, 100')>0)
        result_noise1,errors = video_tools.formMaskDiff(fileOne,
                                          modFiles[2],
                                          modFiles[2],
                                          'AddNoise',
                                          startSegment=None,
                                          endSegment=None,
                                          analysis=analysis,
                                          alternateFunction=None,
                                          arguments={})
        self.assertTrue(len(result_noise1)>= 1)
        self.assertEqual(result_noise1[0]['endframe']-result_noise1[0]['startframe'], result_noise1[0]['frames'])
        self.assertEqual(20, result_noise1[0]['startframe'])
        #self.assertEqual(81, result_noise1[0]['endframe'])
        result_noise2,errors = video_tools.formMaskDiff(fileOne,
                                          modFiles[2],
                                          modFiles[2],
                                          'AddNoise',
                                          startSegment=None,
                                          endSegment=None,
                                          analysis=analysis,
                                          alternateFunction=video_tools.detectCompare,
                                          arguments={})
        self.assertTrue(len(result_noise2) >= 1)
        self.assertEqual(result_noise2[0]['endframe'] - result_noise2[0]['startframe'], result_noise2[0]['frames'])
        self.assertEqual(20, result_noise1[0]['startframe'])


    """
    def testAudio(self):
        from maskgen.tool_set import  VidTimeManager
        video_tools.audioWrite('test_ta.0.0.wav',512)
        self.filesToKill.append('test_ta2.0.0.wav')
        self.filesToKill.append('test_ta.0.0.wav')
        self.filesToKill.append('test_ta3.0.0.wav')
        self.filesToKill.append('test_ta4.0.0.wav')
        self.filesToKill.append('test_ta5.0.0.wav')
        augmentAudio('test_ta.0.0.wav','test_ta2.0.0.wav',addNoise)
        augmentAudio('test_ta.0.0.wav', 'test_ta3.0.0.wav', sampleFrames)
        singleChannelSample('test_ta.0.0.wav','test_ta4.0.0.wav')
        singleChannelSample('test_ta.0.0.wav', 'test_ta5.0.0.wav',skip=2)
        result,errors = video_tools.audioCompare('test_ta.0.0.wav','test_ta2.0.0.wav','test_ta_c',VidTimeManager())
        self.assertEqual(1,len(result))
        self.assertEqual(7,result[0]['startframe'])
        self.assertEqual(result[0]['endframe'], result[0]['startframe'] + result[0]['frames'])

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta3.0.0.wav', 'test_ta_s1', VidTimeManager())
        self.assertEqual(1, len(result))
        self.assertEqual(6, result[0]['startframe'])
        self.assertEqual(result[0]['endframe'], result[0]['startframe'] + result[0]['frames'])

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta4.0.0.wav', 'test_ta_s2', VidTimeManager())
        self.assertEqual(1, len(result))
        self.assertEqual(6, result[0]['startframe'])
        self.assertEqual(result[0]['endframe'], result[0]['startframe'] + result[0]['frames'])

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta5.0.0.wav', 'test_ta_s3', VidTimeManager(),
                                                 arguments={'Copy Stream':'right'})
        self.assertEqual(1, len(result))
        self.assertEqual(6, result[0]['startframe'])
        self.assertEqual(result[0]['endframe'], result[0]['startframe'] + result[0]['frames'])


    def tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)
if __name__ == '__main__':
    unittest.main()
