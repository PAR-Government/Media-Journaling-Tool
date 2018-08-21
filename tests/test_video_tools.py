from maskgen import video_tools,tool_set
import unittest
import numpy as np
import cv2
import os
from test_support import TestSupport
from maskgen.ffmpeg_api import getDuration

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

def changeForTest(frame,no):
    if no >= 20 and no < 40:
        return np.random.randint(255, size=(1090, 1920, 3)).astype('uint8')
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

def insertAudio(filename,outfilname,pos,length):
    import wave
    import struct
    import ctypes
    import random
    fone = wave.open(filename, 'rb')
    countone = fone.getnframes()
    onechannels = fone.getnchannels()
    onewidth = fone.getsampwidth()
    ftwo = wave.open(outfilname, 'wb')
    ftwo.setparams(fone.getparams())
    pos = pos * onechannels * onewidth
    length = length * onechannels * onewidth
    position = 0
    while countone>0:
        toRead = min([1024,countone])
        countone -= toRead
        framesone = fone.readframes(toRead)
        position += toRead
        if length > 0 and position > pos:
            ftwo.writeframes(framesone[0:pos])
            while(length > 0):
                value = random.randint(-32767, 32767)
                packed_value = struct.pack('h', value)
                ftwo.writeframesraw(packed_value)
                length-=1
            ftwo.writeframes(framesone[pos:])
        else:
            ftwo.writeframes(framesone)
    fone.close()
    ftwo.close()

class TestVideoTools(TestSupport):
    filesToKill = []

    def setUp(self):
        source = self.locateFile('tests/videos/sample1.mov')
        target = 'sample1_ffr.mov'
        os.system('ffmpeg -y -i "{}"  -r 10/1  "{}"'.format(source, target))
        self.addFileToRemove(target)
        source = self.locateFile('tests/videos/sample1.mov')
        target = 'sample1_ffr_2.mov'
        os.system('ffmpeg -y -i "{}"  -r 8/1  "{}"'.format(source, target))
        self.addFileToRemove(target)

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

    def _add_mask_files_to_kill(self, segments):
        for segment in segments:
            if 'videosegment' in segment:
                self.filesToKill.append(segment['videosegment'])

    def _init_write_video_file(self, name, alter_funcs):
        try:
            files = []
            writer_main  = tool_set.GrayFrameWriter(name,30/1.0, preferences={'vid_suffix':'avi','vid_codec':'raw'})
            rate = 1/30.0
            main_count = 0
            counters_for_all = [0 for i in alter_funcs]
            writers = [ tool_set.GrayFrameWriter(name+str(func).split()[1],30/1.0,preferences={'vid_suffix':'avi','vid_codec':'raw'}) for func in alter_funcs]
            for i in range(100):
                mask = np.random.randint(255, size=(1090, 1920,3)).astype('uint8')
                writer_main.write(mask, main_count*rate)
                nextcounts = []
                for writer,func,counter in zip(writers,alter_funcs,counters_for_all):
                    result = func(mask, i + 1)
                    if type(result) == list:
                        for item in result:
                            writer.write(item, counter * rate)
                            counter+=1
                        nextcounts.append(counter)
                    else:
                        writer.write(result,counter*rate )
                        nextcounts.append(counter+1)
                counters_for_all=nextcounts
                main_count += 1
        except Exception as ex:
            print ex
        finally:
            writer_main.close()
            for writer in writers:
                files.append(writer.filename)
                writer.close()
        self.filesToKill.append(writer_main.filename)
        self.filesToKill.extend(files)
        return writer_main.filename, files

    def test_duration(self):
        expected = 59350
        duration = getDuration(self.locateFile('tests/videos/sample1.mov'))
        self.assertTrue(abs(duration - expected) < 1)
        duration = getDuration(self.locateFile('tests/videos/sample1.mov'),audio=True)
        self.assertTrue(abs(duration - expected) < 2)

    def test_meta(self):
        meta,frames = video_tools.getMeta(self.locateFile('tests/videos/sample1.mov'), with_frames=True)
        self.assertEqual(803, len(frames['0']))
        meta,frames = video_tools.getMeta(self.locateFile('tests/videos/sample1.mov'),show_streams=True)
        self.assertEqual('yuv420p',meta[0]['pix_fmt'])


    def test_orientation(self):
        video_tools.get_video_orientation_change('sample1_ffr.mov','sample1_ffr.mov')

    def test_frame_count(self):

        result = video_tools.getFrameCount('sample1_ffr.mov',(0,21),(0,593))
        self.assertEqual(59200.0, round(result['endtime']))
        self.assertEqual(573, result['frames'])
        self.assertEqual(593, result['endframe'])
        self.assertEqual(2000.0, result['starttime'])
        self.assertEqual(21, result['startframe'])

        result = video_tools.getFrameCount('sample1_ffr.mov',(2010,0),(59200,0))
        self.assertEqual(59200.0, round(result['endtime']))
        self.assertEqual(573, result['frames'])
        self.assertEqual(593, result['endframe'])
        self.assertEqual(2000.0, result['starttime'])
        self.assertEqual(21, result['startframe'])

        result = video_tools.getFrameCount('sample1_ffr.mov',(0,21), None)
        self.assertEqual(576, result['frames'])
        self.assertEqual(596, result['endframe'])
        self.assertEqual(59500.0, result['endtime'])
        self.assertEqual(2000.0, result['starttime'])
        self.assertEqual(21, result['startframe'])

        result = video_tools.getFrameCount('sample1_ffr.mov', (2010, 0), None)
        self.assertEqual(576, result['frames'])
        self.assertEqual(596, result['endframe'])
        self.assertEqual(59500.0, result['endtime'])
        self.assertEqual(2000.0, result['starttime'])
        self.assertEqual(21, result['startframe'])

    def test_frame_binding_ffr(self):

        result = video_tools.getMaskSetForEntireVideo('sample1_ffr.mov',
                                                      start_time='00:00:02.01',
                                                      end_time='00:00:59.29')
        self._add_mask_files_to_kill(result)
        self.assertEqual(59200.0, round(result[0]['endtime']))
        self.assertEqual(573, result[0]['frames'])
        self.assertEqual(593, result[0]['endframe'])
        self.assertEqual(2000.0, result[0]['starttime'])
        self.assertEqual(21, result[0]['startframe'])

        result = video_tools.getMaskSetForEntireVideo('sample1_ffr.mov',
                                                      start_time='00:00:02.01:02')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2200.0, round(result[0]['starttime']))
        self.assertEqual(59500.0, round(result[0]['endtime']))
        self.assertEqual(23, result[0]['startframe'])
        self.assertEqual(574, result[0]['frames'])

        result = video_tools.getMaskSetForEntireVideo('sample1_ffr.mov',
                                                      start_time='00:00:02.01')
        self._add_mask_files_to_kill(result)
        self.assertEqual(576, result[0]['frames'])
        self.assertEqual(596, result[0]['endframe'])
        self.assertEqual(59500.0, result[0]['endtime'])
        self.assertEqual(2000.0, result[0]['starttime'])
        self.assertEqual(21, result[0]['startframe'])

        result = video_tools.getMaskSetForEntireVideo('sample1_ffr.mov', start_time='23',
                                                      end_time='29')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2200.0, round(result[0]['starttime']))
        self.assertEqual(23, result[0]['startframe'])
        self.assertEqual(2800.0, round(result[0]['endtime']))
        self.assertEqual(29, result[0]['endframe'])
        self.assertEqual(29 - 23 + 1, result[0]['frames'])

        result = video_tools.getMaskSetForEntireVideo('videos/Sample2_ffr.mxf', start_time=21, end_time=None) #ffr vid with 'N/A' nbframes.
        self._add_mask_files_to_kill(result)
        self.assertEqual(567.0, round(result[0]['starttime']))
        self.assertEqual(21, result[0]['startframe'])
        self.assertEqual(44975.0, round(result[0]['endtime']))
        self.assertEqual(1350, result[0]['endframe'])
        self.assertEqual(1350 - 21 + 1, result[0]['frames'])

    def test_frame_binding_vfr(self):

        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov')) #Variable FR
        self._add_mask_files_to_kill(result)
        self.assertEqual(0.0, result[0]['starttime'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(803,result[0]['frames'])
        self.assertEqual(803.0, result[0]['endframe'])
        self.assertEqual(59348.0, round(result[0]['endtime']))
        self.assertEqual('video', result[0]['type'])

        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1_slow.mov')) #Constant FR
        self._add_mask_files_to_kill(result)
        self.assertEqual(0.0, result[0]['starttime'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(596, result[0]['frames'])
        self.assertEqual(596, result[0]['endframe'])
        self.assertEqual(59500.0, result[0]['endtime'])
        self.assertEqual('video', result[0]['type'])

        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1_slow.mov'),
                                                      start_time='00:00:02.01')  # Constant FR
        self._add_mask_files_to_kill(result)
        self.assertEqual(2000.0, result[0]['starttime'])
        self.assertEqual(21, result[0]['startframe'])
        self.assertEqual(576, result[0]['frames'])
        self.assertEqual(596, result[0]['endframe'])
        self.assertEqual(59500.0, result[0]['endtime'])
        self.assertEqual('video', result[0]['type'])

        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1_swap.mov'),
                                                      start_time='00:00:02.01', end_time='00:00:59.29')  # Variable FR, swapped streams, fails to grab all frames
        self._add_mask_files_to_kill(result)
        self.assertEqual(59221.0, round(result[0]['endtime']))
        self.assertEqual(779, result[0]['frames'])
        self.assertEqual(801, result[0]['endframe'])
        self.assertEqual(23, result[0]['startframe'])
        self.assertEqual(1982.0, round(result[0]['starttime']))

        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1_swap.mov'),
                                                      start_time='00:00:02.01') #Variable FR, swapped streams.
        self._add_mask_files_to_kill(result)
        self.assertEqual(1982.0, round(result[0]['starttime']))
        self.assertEqual(23, result[0]['startframe'])
        self.assertEqual(803 - 23 + 1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov'),start_time='00:00:02.01')
        self._add_mask_files_to_kill(result)
        self.assertEqual(1982.0, round(result[0]['starttime']))
        self.assertEqual(23, result[0]['startframe'])
        self.assertEqual(803-23+1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov'), start_time='00:00:02.01:02')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2123.0, round(result[0]['starttime']))
        self.assertEqual(24, result[0]['startframe'])
        self.assertEqual(780, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov'), start_time='00:00:02.01',end_time='00:00:04.01')
        self._add_mask_files_to_kill(result)
        self.assertEqual(1982.0, round(result[0]['starttime']))
        self.assertEqual(23, result[0]['startframe'])
        self.assertEqual(3965.0, round(result[0]['endtime']))
        self.assertEqual(47, result[0]['endframe'])
        self.assertEqual(47-23+1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov'), start_time='23',end_time='29')
        self._add_mask_files_to_kill(result)
        self.assertEqual(1982.0, round(result[0]['starttime']))
        self.assertEqual(23, result[0]['startframe'])
        self.assertEqual(2548.0, round(result[0]['endtime']))
        self.assertEqual(29, result[0]['endframe'])
        self.assertEqual(29 - 23 + 1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov'), start_time='29',end_time='55')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2548.0, round(result[0]['starttime']))
        self.assertEqual(29, result[0]['startframe'])
        self.assertEqual(4532.0, round(result[0]['endtime']))
        self.assertEqual(55, result[0]['endframe'])
        self.assertEqual(55 - 29 + 1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov'), start_time='29')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2548.0, round(result[0]['starttime']))
        self.assertEqual(29, result[0]['startframe'])
        self.assertEqual(59348.0, round(result[0]['endtime']))
        self.assertEqual(803, result[0]['endframe'])
        self.assertEqual(803 - 29 + 1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov'),
                                                      media_types=['audio'])
        self._add_mask_files_to_kill(result)
        self.assertEqual(0.0, result[0]['starttime'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(2617262, result[0]['frames'])
        self.assertEqual(2617262, result[0]['endframe'])
        self.assertEqual(59348.0, round(result[0]['endtime']))
        self.assertEqual('audio', result[0]['type'])
        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov'),
                                                      start_time='1',
                                                      media_types=['video'])
        self._add_mask_files_to_kill(result)
        self.assertEqual(0.0, result[0]['starttime'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(803, result[0]['frames'])
        self.assertEqual(803, result[0]['endframe'])
        self.assertEqual(59348.0, round(result[0]['endtime']))
        self.assertEqual('video', result[0]['type'])
        result = video_tools.getMaskSetForEntireVideo(self.locateFile('tests/videos/sample1.mov'), start_time='00:00:02.01',
                                                      end_time='00:00:04',
                                                      media_types=['audio'])
        self._add_mask_files_to_kill(result)
        self.assertEqual(2010.0, round(result[0]['starttime']))
        self.assertEqual(88641, result[0]['startframe'])
        self.assertEqual(4000.0, round(result[0]['endtime']))
        self.assertEqual(176400, result[0]['endframe'])
        self.assertEqual(176400 - 88641 + 1, result[0]['frames'])

    def test_remove_intersection(self):
        setOne = []
        maskitem= {}
        maskitem['starttime'] = 900
        maskitem['startframe'] = 10
        maskitem['endtime'] = 2900
        maskitem['endframe'] = 30
        maskitem['frames'] = 21
        maskitem['rate'] = 10
        maskitem['type'] = 'video'
        setOne.append(maskitem)
        maskitem = dict()
        maskitem['starttime'] = 4900
        maskitem['startframe'] = 50
        maskitem['endtime'] = 6900
        maskitem['endframe'] = 70
        maskitem['frames'] = 21
        maskitem['rate'] = 10
        maskitem['type'] = 'video'
        setOne.append(maskitem)

        setTwo = []
        maskitem = {}
        maskitem['starttime'] = 0
        maskitem['startframe'] = 1
        maskitem['endtime'] = 500
        maskitem['endframe'] = 6
        maskitem['frames'] = 6
        maskitem['rate'] = 10
        maskitem['type'] = 'video'
        setTwo.append(maskitem)
        maskitem = dict()
        maskitem['starttime'] = 800
        maskitem['startframe'] = 9
        maskitem['endtime'] = 1400
        maskitem['endframe'] = 15
        maskitem['frames'] = 7
        maskitem['rate'] = 10
        maskitem['type'] = 'video'
        setTwo.append(maskitem)
        maskitem = dict()
        maskitem['starttime'] = 2400
        maskitem['startframe'] = 25
        maskitem['endtime'] = 3400
        maskitem['endframe'] = 35
        maskitem['frames'] =11
        maskitem['rate'] = 10
        maskitem['type'] = 'video'
        setTwo.append(maskitem)
        maskitem = dict()
        maskitem['starttime'] = 3200
        maskitem['startframe'] = 44
        maskitem['endtime'] = 4600
        maskitem['endframe'] = 47
        maskitem['frames'] = 4
        maskitem['rate'] = 10
        maskitem['type'] = 'video'
        setTwo.append(maskitem)
        maskitem = dict()
        maskitem['starttime'] = 8900
        maskitem['startframe'] = 90
        maskitem['endtime'] = 9400
        maskitem['endframe'] = 95
        maskitem['frames'] = 6
        maskitem['rate'] = 10
        maskitem['type'] = 'video'
        setTwo.append(maskitem)

        finalsets = video_tools.removeIntersectionOfMaskSets(setOne,setTwo)
        self.assertEquals(6,len(finalsets))
        self.assertEqual([
            {'endframe': 6, 'rate': 10, 'starttime': 0, 'frames': 6, 'startframe': 1, 'endtime': 500, 'type': 'video'},
            {'endframe': 9, 'rate': 10, 'starttime': 800, 'frames': 1, 'startframe': 9, 'endtime': 800.0,
             'type': 'video'},
            {'endframe': 30, 'rate': 10, 'starttime': 900, 'frames': 21, 'startframe': 10, 'endtime': 2900,
             'type': 'video'},
            {'endframe': 47, 'rate': 10, 'starttime': 3200, 'frames': 4, 'startframe': 44, 'endtime': 4600,
             'type': 'video'},
            {'endframe': 70, 'rate': 10, 'starttime': 4900, 'frames': 21, 'startframe': 50, 'endtime': 6900,
             'type': 'video'},
            {'endframe': 95, 'rate': 10, 'starttime': 8900, 'frames': 6, 'startframe': 90, 'endtime': 9400,
             'type': 'video'}],finalsets)

    def test_before_dropping(self):
        amount = 30
        fileOne = self._init_write_file('test_ts_bd1',2500,75,30,30)
        fileTwo = self._init_write_file('test_ts_bd2', 4100,123,27,30)
        sets= []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 30
        change['error'] = 1.1
        change['videosegment'] = ''
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount -1
        change['frames'] = amount
        change['rate'] = 30
        change['error'] = 1.2
        change['videosegment'] = fileOne
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 4100
        change['startframe'] = 123
        change['endtime'] = 5000
        change['endframe'] = change['startframe'] + 27 -1
        change['frames'] = int(27)
        change['rate'] = 30
        change['error'] = 1.3
        change['videosegment'] = fileTwo
        change['type'] = 'video'
        sets.append(change)

        result  = video_tools.dropFramesFromMask([{
            'startframe':90,
            'starttime':3000,
            'endframe':117,
            'endtime': 4000
        }],sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(3, len(result))
        self.assertEqual(15,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(89, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(122, result[2]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.3, result[2]['error'])
        self.assertEqual(1.2, result[1]['error'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        }],sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(3, len(result))
        self.assertEqual(15, result[1]['frames'])
        self.assertEqual(63, result[1]['startframe'])
        self.assertEqual(77, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(122, result[2]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.3, result[2]['error'])
        self.assertEqual(1.2, result[1]['error'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }],sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(4, len(result))
        self.assertEqual(12,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(86, result[1]['endframe'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(87, result[2]['startframe'])
        self.assertEqual(98, result[2]['endframe'])
        self.assertEqual(117, result[3]['startframe'])
        self.assertEqual(143, result[3]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])
        self.assertEqual(1.2, result[2]['error'])
        self.assertEqual(1.3, result[3]['error'])


        result = video_tools.dropFramesFromMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }], sets,keepTime=True)
        self._add_mask_files_to_kill(result)
        self.assertEqual(4, len(result))
        self.assertEqual(12, result[1]['frames'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(86, result[1]['endframe'])
        self.assertEqual(93, result[2]['startframe'])
        self.assertEqual(104, result[2]['endframe'])
        self.assertEqual(123, result[3]['startframe'])
        self.assertEqual(149, result[3]['endframe'])
        self.assertEqual(4, len(result))
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])
        self.assertEqual(1.2, result[2]['error'])
        self.assertEqual(1.3, result[3]['error'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }], sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(12, result[0]['endframe'])
        self.assertEqual(31, result[1]['startframe'])
        self.assertEqual(57, result[1]['endframe'])
        self.assertEqual(1.2, result[0]['error'])
        self.assertEqual(1.3, result[1]['error'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 93,
            'starttime': 3100
        }], sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(30, result[0]['endframe'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(92, result[1]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }], sets,keepTime=True)
        self._add_mask_files_to_kill(result)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(93, result[0]['startframe'])
        self.assertEqual(104, result[0]['endframe'])
        self.assertEqual(123, result[1]['startframe'])
        self.assertEqual(149, result[1]['endframe'])
        self.assertEqual(1.2, result[0]['error'])
        self.assertEqual(1.3, result[1]['error'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 93,
            'starttime': 3100,
        }], sets,keepTime=True)
        self._add_mask_files_to_kill(result)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(30, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(92, result[1]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])



    def test_before_dropping_nomask(self):
        amount = 30
        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        change['error'] = 1.1
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount - 1
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        change['error'] = 1.2
        sets.append(change)
        change = dict()
        change['starttime'] = 4100
        change['startframe'] = 123
        change['endtime'] = 5000
        change['endframe'] = change['startframe'] + 27 -1
        change['frames'] = int(27)
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        change['error'] = 1.3
        sets.append(change)
        result  = video_tools.dropFramesWithoutMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 92,
            'endtime': 3100
        }],sets)
        self.assertEqual(4, len(result))
        self.assertEqual(12,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(86, result[1]['endframe'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(87, result[2]['startframe'])
        self.assertEqual(98, result[2]['endframe'])
        self.assertEqual(117, result[3]['startframe'])
        self.assertEqual(143, result[3]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])
        self.assertEqual(1.2, result[2]['error'])
        self.assertEqual(1.3, result[3]['error'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        }],  sets)
        self.assertEqual(3, len(result))
        self.assertEqual(14, result[1]['frames'])
        self.assertEqual(63, result[1]['startframe'])
        self.assertEqual(76, result[1]['endframe'])
        self.assertEqual(95, result[2]['startframe'])
        self.assertEqual(121, result[2]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])
        self.assertEqual(1.3, result[2]['error'])

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
        self.assertEqual(86,  result[1]['endframe'])
        self.assertEqual(93,  result[2]['startframe'])
        self.assertEqual(104, result[2]['endframe'])
        self.assertEqual(123, result[3]['startframe'])
        self.assertEqual(149, result[3]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])
        self.assertEqual(1.2, result[2]['error'])
        self.assertEqual(1.3, result[3]['error'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }],  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(11, result[0]['frames'])
        self.assertEqual(1,  result[0]['startframe'])
        self.assertEqual(11, result[0]['endframe'])
        self.assertEqual(30, result[1]['startframe'])
        self.assertEqual(56, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 93,
            'starttime': 3100
        }] , sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(30, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(92, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }],  sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(93, result[0]['startframe'])
        self.assertEqual(104, result[0]['endframe'])
        self.assertEqual(123, result[1]['startframe'])
        self.assertEqual(149, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 93,
            'starttime': 3100
        }], sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(30, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(92, result[1]['endframe'])

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
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])
        self._add_mask_files_to_kill(result)

        result = func([{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[1]['frames'])
        self.assertEqual(103, result[1]['startframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])
        self._add_mask_files_to_kill(result)

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
        self.assertEqual(112, result[2]['startframe'])
        self.assertEqual(135, result[2]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])
        self.assertEqual(1.2, result[2]['error'])
        self._add_mask_files_to_kill(result)

        result = func([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 63,
            'endtime': 2100
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(30, result[1]['frames'])
        self.assertEqual(64, result[0]['startframe'])
        self.assertEqual(93, result[0]['endframe'])
        self.assertEqual(138, result[1]['startframe'])
        self.assertEqual(167, result[1]['endframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.2, result[1]['error'])
        self._add_mask_files_to_kill(result)


    def test_cutCompare(self):

        source = 'sample1_ffr.mov'
        video_tools.runffmpeg(['-y', '-i', source, '-ss', '00:00:00.00', '-t', '10', 'part1.mov'])
        video_tools.runffmpeg(['-y', '-i', source, '-ss', '00:00:12.00', 'part2.mov'])
        video_tools.runffmpeg(['-y', '-i', 'part1.mov', '-i', 'part2.mov', '-filter_complex',
                               '[0:v][0:a][1:v][1:a] concat=n=2:v=1:a=1 [outv] [outa]',
                               '-map', '[outv]', '-map', '[outa]', 'sample1_cut_full.mov'])
        self.filesToKill.append('part1.mov')
        self.filesToKill.append('part2.mov')
        self.filesToKill.append('sample1_cut_full.mov')
        maskSet, errors = video_tools.cutCompare(source, 'sample1_cut_full.mov', 'sample1',
                                                 tool_set.VidTimeManager(startTimeandFrame=(10000, 0),
                                                                         stopTimeandFrame=(12000, 0)))
        audioSet = [mask for mask in maskSet if mask['type'] == 'audio']
        print(maskSet[0])
        print(audioSet[0])
        self.assertEqual(1, len(audioSet))
        self.assertEqual(87053, audioSet[0]['frames'])
        self.assertEqual(441001, audioSet[0]['startframe'])
        self.assertEqual(441001+87053-1, audioSet[0]['endframe'])
        self.assertEquals(audioSet[0]['starttime'], maskSet[0]['starttime'])
        self.assertTrue(0.2 > abs(audioSet[0]['endtime'] / 1000.0 - maskSet[0]['endtime'] / 1000.0))
        self.assertEqual(44100.0, audioSet[0]['rate'])
        videoSet = [mask for mask in maskSet if mask['type'] == 'video']
        self.assertEqual(20, videoSet[0]['frames'])
        self.assertEqual(101, videoSet[0]['startframe'])
        self.assertEqual(120, videoSet[0]['endframe'])

        source = self.locateFile('tests/videos/sample1.mov')
        video_tools.runffmpeg(['-y','-i',source,'-ss','00:00:00.00', '-t','10','part1.mov'])
        video_tools.runffmpeg(['-y','-i', source, '-ss', '00:00:12.00', 'part2.mov'])
        video_tools.runffmpeg(['-y','-i', 'part1.mov', '-i','part2.mov','-filter_complex',
                               '[0:v][0:a][1:v][1:a] concat=n=2:v=1:a=1 [outv] [outa]',
                               '-map','[outv]','-map','[outa]','sample1_cut_full.mov'])
        self.filesToKill.append('part1.mov')
        self.filesToKill.append('part2.mov')
        self.filesToKill.append('sample1_cut_full.mov')
        maskSet, errors = video_tools.cutCompare(source,'sample1_cut_full.mov','sample1',tool_set.VidTimeManager(startTimeandFrame=(10000,0),
                                                                                       stopTimeandFrame=(12000,0)))
        audioSet = [mask for mask in  maskSet if mask['type']=='audio']
        print(maskSet[0])
        print(audioSet[0])
        self.assertEqual(1, len(audioSet))
        self.assertEqual(85526, audioSet[0]['frames'])
        self.assertEqual(440339, audioSet[0]['startframe'])
        self.assertEqual(440339+85526-1, audioSet[0]['endframe'])
        self.assertEquals(audioSet[0]['starttime'],maskSet[0]['starttime'])
        self.assertTrue(0.2 > abs(audioSet[0]['endtime']/1000.0-maskSet[0]['endtime']/1000.0))
        self.assertEqual(44100.0, audioSet[0]['rate'])






    def test_cut(self):
        sets = []
        change = dict()
        change['starttime'] = 3078.1
        change['startframe'] = 94
        change['endtime'] = 3111.4
        change['endframe'] = 95
        change['frames'] = 2
        change['rate'] = 30
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 3078.1
        change['startframe'] = 94
        change['endtime'] = 3263.4
        change['endframe'] = 99
        change['frames'] = 5
        change['rate'] = 30
        change['type'] = 'video'
        result = video_tools.insertFrames([change], sets)
        self.assertEqual(100, result[0]['startframe'])
        self.assertEqual(101, result[0]['endframe'])
        self.assertAlmostEqual(3296.73, result[0]['starttime'],places=2)
        self.assertAlmostEqual(3330.03, result[0]['endtime'],places=2)
        sets = []
        change = dict()
        change['starttime'] = 3078.1
        change['startframe'] = 94
        change['endtime'] = 3111.4
        change['endframe'] = 95
        change['frames'] = 2
        change['rate'] = 30
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 3296.7
        change['startframe'] = 96
        change['endtime'] = 3296.7
        change['endframe'] = 96
        change['frames'] = 2
        change['rate'] = 30
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 3111.4
        change['startframe'] = 95
        change['endtime'] = 3111.4
        change['endframe'] = 95
        change['frames'] = 1
        change['rate'] = 30
        change['type'] = 'video'
        result = video_tools.insertFrames([change], sets)
        self.assertEqual(94, result[0]['startframe'])
        self.assertEqual(94, result[0]['endframe'])
        self.assertEqual(96, result[1]['startframe'])
        self.assertEqual(96, result[1]['endframe'])
        self.assertEqual(97, result[2]['startframe'])
        self.assertEqual(97, result[2]['endframe'])
        self.assertAlmostEqual(3144.73, result[1]['starttime'], places=2)
        self.assertAlmostEqual(3144.73, result[1]['endtime'], places=2)
        self.assertAlmostEqual(3330.03, result[2]['starttime'],places=2)
        self.assertAlmostEqual(3330.03, result[2]['endtime'], places=2)


        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 3111.4
        change['endframe'] = 95
        change['frames'] = 2
        change['rate'] = 30
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = -33.333
        change['endframe'] = 0
        change['frames'] = 0
        change['rate'] = 30
        change['type'] = 'video'
        result = video_tools.insertFrames([change], sets)
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(95, result[0]['endframe'])
        self.assertAlmostEqual(3111.40, result[0]['endtime'],places=2)
        self.assertAlmostEqual(0, result[0]['starttime'],places=2)

    def test_after_dropping(self):
        amount = 30
        fileOne = self._init_write_file('test_ts_bd1', 0, 1, 30, 30)
        fileTwo = self._init_write_file('test_ts_bd2', 2500, 75, 30, 30)
        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 1000
        change['endframe'] = amount
        change['frames'] = amount
        change['rate'] = 30
        change['type'] = 'video'
        change['error'] = 1.1
        change['videosegment'] = fileOne
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount - 1
        change['frames'] = amount
        change['rate'] = 30
        change['error'] = 1.2
        change['type'] = 'video'
        change['videosegment'] = fileTwo
        sets.append(change)
        self.after_general_all(sets,video_tools.insertFrames)

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
        change['error'] = 1.1
        change['videosegment'] = fileOne
        result = video_tools.resizeMask([change], (1000, 1720))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        self.assertEqual(1.1, result[0]['error'])

    def test_crop(self):
        fileOne = self._init_write_file('test_td_rs', 0, 1, 30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['type'] = 'video'
        change['error'] = 1.1
        change['videosegment'] = fileOne
        result = video_tools.cropMask([change], (100, 100, 900, 1120))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        self.assertEqual(1.1, result[0]['error'])
        self._add_mask_files_to_kill(result)
        result = video_tools.insertMask([change], (100, 100, 900, 1120), (1090, 1920))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        self.assertEqual(1.1, result[0]['error'])
        self._add_mask_files_to_kill(result)

    def test_rotate(self):
        fileOne = self._init_write_file('test_td_rs', 0, 1,30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['error'] = 1.1
        change['type'] = 'video'
        change['videosegment'] = fileOne
        result = video_tools.rotateMask(-90,[change],expectedDims=(1920,1090))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        self.assertEqual(1.1, result[0]['error'])
        self._add_mask_files_to_kill(result)



    def test_reverse(self):

        result = video_tools.reverseMasks([{
            'startframe': 0,
            'starttime': 0,
            'endframe': 130,
            'error':1.1,
            'endtime': 4333
        }], [{'starttime':0,
              'startframe': 0,
              'endframe': 130,
              'error':1.1,
              'endtime': 4333,
              'type':'video'}])
        self.assertEqual(1,len(result))
        self.assertEqual(4333,result[0]['endtime'])
        self.assertEqual(130, result[0]['endframe'])
        self.assertEqual(1.1, result[0]['error'])

        amount = 30
        fileOne = self._init_write_file('test_tr1',2500,75,30,30)
        fileTwo = self._init_write_file('test_tr2', 4100, 123, 30, 27)
        sets = []
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount -1
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = fileOne
        change['type'] = 'video'
        change['error'] = 1.1
        sets.append(change)
        change = dict()
        change['starttime'] = 4100
        change['startframe'] = 123
        change['endtime'] = 5000
        change['endframe'] = 149
        change['frames'] = int(27)
        change['rate'] = 30
        change['videosegment'] = fileTwo
        change['type'] = 'video'
        change['error'] = 1.2
        sets.append(change)

        result = video_tools.reverseMasks([{
            'startframe': 90,
            'starttime': 3000,
            'endframe': 130,
            'endtime': 4333
        }], sets)
        self.assertEqual(4, len(result))
        self.assertEqual(15, result[0]['frames'])
        self.assertEqual(75, result[0]['startframe'])
        self.assertEqual(89, result[0]['endframe'])
        self.assertEqual(15, result[1]['frames'])
        self.assertEqual(130, result[1]['endframe'])
        self.assertEqual(116, result[1]['startframe'])
        self.assertEqual(8, result[2]['frames'])
        self.assertEqual(97, result[2]['endframe'])
        self.assertEqual(90, result[2]['startframe'])
        self.assertEqual(19, result[3]['frames'])
        self.assertEqual(149, result[3]['endframe'])
        self.assertEqual(131, result[3]['startframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.1, result[1]['error'])
        self.assertEqual(1.2, result[2]['error'])
        self.assertEqual(1.2, result[3]['error'])
        self._add_mask_files_to_kill(result)

        reader_orig = tool_set.GrayBlockReader(sets[0]['videosegment'])
        reader_new = tool_set.GrayBlockReader(result[0]['videosegment'])
        while True:
            orig_mask = reader_orig.read()
            if orig_mask is None:
                break
            new_mask = reader_new.read()
            if new_mask is None:
                break
            is_equal = np.all(orig_mask == new_mask)
            self.assertTrue(is_equal)
        reader_new.close()
        reader_new = tool_set.GrayBlockReader(result[1]['videosegment'])
        reader_new.close()
        reader_new = tool_set.GrayBlockReader(result[2]['videosegment'])
        reader_new.close()
        reader_new = tool_set.GrayBlockReader(result[3]['videosegment'])
        reader_new.close()
        reader_orig.close()

        for item in sets:
            item.pop('videosegment')
        result = video_tools.reverseMasks([{
            'startframe': 90,
            'starttime': 3000,
            'endframe': 130,
            'endtime': 4333
        }], sets)
        self.assertEqual(4, len(result))
        self.assertEqual(15, result[0]['frames'])
        self.assertEqual(75, result[0]['startframe'])
        self.assertEqual(89, result[0]['endframe'])
        self.assertEqual(15, result[1]['frames'])
        self.assertEqual(130, result[1]['endframe'])
        self.assertEqual(116, result[1]['startframe'])
        self.assertEqual(8, result[2]['frames'])
        self.assertEqual(97, result[2]['endframe'])
        self.assertEqual(90, result[2]['startframe'])
        self.assertEqual(19, result[3]['frames'])
        self.assertEqual(149, result[3]['endframe'])
        self.assertEqual(131, result[3]['startframe'])
        self.assertEqual(1.1, result[0]['error'])
        self.assertEqual(1.1, result[1]['error'])
        self.assertEqual(1.2, result[2]['error'])
        self.assertEqual(1.2, result[3]['error'])
        self._add_mask_files_to_kill(result)


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
        change['error'] = 1.1
        change['type'] = 'video'
        change['videosegment'] = fileOne
        result = video_tools.invertVideoMasks([change], 'x','y')
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        self.assertEqual(1.1, result[0]['error'])
        reader = tool_set.GrayBlockReader(result[0]['videosegment'])
        self._add_mask_files_to_kill(result)
        mask = reader.read()
        self.assertEqual(2,reader.current_frame())
        self.assertEqual(33, reader.current_frame_time())
        self.assertTrue(np.all(255-mask == start_set[0]))
        reader.close()


    def test_all_mods(self):
        mod_functions = [sameForTest,cropForTest,noiseForTest,addForTest,changeForTest]
        #fileOne,modFiles = 'test_td_rs_mask_0.0.avi',['test_td_rssameForTest_mask_0.0.avi',
        #                                              'test_td_rscropForTest_mask_0.0.avi',
        #                                              'test_td_rsnoiseForTest_mask_0.0.avi',
        #                                              'test_td_rsaddForTest_mask_0.0.avi']
        fileOne,modFiles = self._init_write_video_file('test_td_rs',mod_functions)
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
                                                      modFiles[4],
                                                      modFiles[4],
                                                      'PasteFrames',
                                                      startSegment=None,
                                                      endSegment=None,
                                                      analysis=analysis,
                                                      alternateFunction=video_tools.pasteCompare,
                                                      arguments={'add type':'replace'})
        self.assertEqual(1, len(result_add))
        self.assertEqual(20, result_add[0]['startframe'])
        self.assertEqual(39, result_add[0]['endframe'])
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
        self.assertEqual(result_noise1[0]['endframe']-result_noise1[0]['startframe']+1, result_noise1[0]['frames'])
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
        self.assertEqual(result_noise2[0]['endframe'] - result_noise2[0]['startframe']+1, result_noise2[0]['frames'])
        self.assertEqual(20, result_noise1[0]['startframe'])


    def testMaseSet(self):
        source = self.locateFile('tests/videos/sample1.mov')
        source_set1 = video_tools.getMaskSetForEntireVideo(source,
                                                      start_time='29',end_time='55')
        source_set2 = video_tools.getMaskSetForEntireVideo(source,
                                                          start_time='29', end_time='55')
        self.assertEquals(source_set1,source_set2)

    def testWarp(self):
        source = self.locateFile('tests/videos/sample1.mov')
        target = 'sample1_ffr.mov'
        source_set = video_tools.getMaskSetForEntireVideo(source,
                                                      start_time='29',end_time='55')
        target_set = video_tools.getMaskSetForEntireVideoForTuples(target,
                                                                   start_time_tuple=(source_set[0]['starttime'], 0),
                                                                   end_time_tuple=(source_set[0]['endtime'], 0))
        print(source_set[0])
        new_mask_set = video_tools._warpMask(source_set, {}, source, source)
        print(new_mask_set[0])
        self.assertTrue(new_mask_set[0]['frames'] == source_set[0]['frames'])
        self.assertTrue(new_mask_set[0]['endtime'] == source_set[0]['endtime'])
        self.assertTrue(new_mask_set[0]['rate'] == source_set[0]['rate'])
        self.assertTrue(new_mask_set[0]['startframe'] == source_set[0]['startframe'])
        self.assertTrue(new_mask_set[0]['starttime'] == source_set[0]['starttime'])
        self._add_mask_files_to_kill(source_set)
        new_mask_set = video_tools._warpMask(source_set,{}, source, target)
        self.assertTrue(new_mask_set[0]['frames'] == target_set[0]['frames'])
        self.assertTrue(new_mask_set[0]['endtime'] == target_set[0]['endtime'])
        self.assertTrue(new_mask_set[0]['rate'] == target_set[0]['rate'])
        self.assertTrue(new_mask_set[0]['startframe'] == target_set[0]['startframe'])
        self.assertTrue(new_mask_set[0]['starttime'] == target_set[0]['starttime'])
        source_mask_set = video_tools._warpMask(new_mask_set, {}, source, target, inverse=True)
        self.assertTrue(abs(source_mask_set[0]['frames'] - source_set[0]['frames']) < 2)
        self.assertTrue(abs(source_mask_set[0]['endtime'] - source_set[0]['endtime']) < source_mask_set[0]['error']*2)
        self.assertTrue(abs(source_mask_set[0]['rate'] - source_set[0]['rate']) < 0.1)
        self.assertTrue(abs(source_mask_set[0]['startframe'] - source_set[0]['startframe']) < 2)
        self.assertTrue(abs(source_mask_set[0]['starttime'] - source_set[0]['starttime']) < source_mask_set[0]['error']*2)
        new_mask_set = video_tools._warpMask(source_set, {}, source, target,useFFMPEG=True)
        self.assertTrue(new_mask_set[0]['frames'] == target_set[0]['frames'])
        self.assertTrue(new_mask_set[0]['endtime'] == target_set[0]['endtime'])
        self.assertTrue(new_mask_set[0]['rate'] == target_set[0]['rate'])
        self.assertTrue(new_mask_set[0]['startframe'] == target_set[0]['startframe'])
        self.assertTrue(new_mask_set[0]['starttime'] == target_set[0]['starttime'])
        source_mask_set = video_tools._warpMask(new_mask_set, {}, source, target, inverse=True,useFFMPEG=True)
        self.assertTrue(abs(source_mask_set[0]['frames'] - source_set[0]['frames']) < 2)
        self.assertTrue(abs(source_mask_set[0]['endtime'] - source_set[0]['endtime']) < source_mask_set[0]['error']*2)
        self.assertTrue(abs(source_mask_set[0]['rate'] - source_set[0]['rate']) < 0.1)
        self.assertTrue(abs(source_mask_set[0]['startframe'] - source_set[0]['startframe']) < 2)
        self.assertTrue(abs(source_mask_set[0]['starttime'] - source_set[0]['starttime']) < source_mask_set[0]['error']*2)

        source_set  = target_set
        source = target
        target = 'sample1_ffr_2.mov'
        target_set = video_tools.getMaskSetForEntireVideoForTuples(target,
                                                               start_time_tuple=(source_set[0]['starttime'], 0),
                                                               end_time_tuple=(source_set[0]['endtime'], 0))
        new_mask_set = video_tools._warpMask(new_mask_set, {}, source, target)
        self.assertTrue(new_mask_set[0]['frames'] == target_set[0]['frames'])
        self.assertTrue(new_mask_set[0]['endtime'] == target_set[0]['endtime'])
        self.assertTrue(new_mask_set[0]['rate'] == target_set[0]['rate'])
        self.assertTrue(new_mask_set[0]['startframe'] == target_set[0]['startframe'])
        self.assertTrue(new_mask_set[0]['starttime'] == target_set[0]['starttime'])

    def testMetaDiff(self):
        video_tools.formMetaDataDiff(self.locateFile('tests/videos/sample1.mov'),self.locateFile('tests/videos/sample1_slow_swap.mov'))
        video_tools.formMetaDataDiff(self.locateFile('tests/videos/sample1.mov'),self.locateFile('tests/videos/sample1_slow_swap.mov'),True,['video'])
        video_tools.formMetaDataDiff(self.locateFile('tests/videos/sample1.mov'),
                                     self.locateFile('tests/videos/sample1_slow_swap.mov'), False, ['audio'])

    def testAudio(self):
        from maskgen.tool_set import  VidTimeManager
        video_tools.audioWrite('test_ta.0.0.wav',512)
        self.filesToKill.append('test_ta2.0.0.wav')
        self.filesToKill.append('test_ta.0.0.wav')
        self.filesToKill.append('test_ta3.0.0.wav')
        self.filesToKill.append('test_ta4.0.0.wav')
        self.filesToKill.append('test_ta5.0.0.wav')
        self.filesToKill.append('test_ta6.0.0.wav')
        augmentAudio('test_ta.0.0.wav','test_ta2.0.0.wav',addNoise)
        augmentAudio('test_ta.0.0.wav', 'test_ta3.0.0.wav', sampleFrames)
        singleChannelSample('test_ta.0.0.wav','test_ta4.0.0.wav')
        singleChannelSample('test_ta.0.0.wav', 'test_ta5.0.0.wav',skip=2)
        insertAudio('test_ta.0.0.wav','test_ta6.0.0.wav',pos=28,length=6)

        result, errors = video_tools.audioInsert('test_ta.0.0.wav', 'test_ta6.0.0.wav', 'test_ta_c', VidTimeManager())
        self.assertEqual(1, len(result))
        self.assertEqual(29, result[0]['startframe'])
        self.assertEqual(48, result[0]['endframe'])
        self.assertEqual(result[0]['endframe'], result[0]['startframe'] + result[0]['frames']-1)

        result,errors = video_tools.audioCompare('test_ta.0.0.wav','test_ta2.0.0.wav','test_ta_c',VidTimeManager())
        self.assertEqual(1,len(result))
        self.assertEqual(7,result[0]['startframe'])
        self.assertEqual(256, result[0]['endframe'])
        self.assertEqual(result[0]['endframe'], result[0]['startframe'] + result[0]['frames']-1)

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta3.0.0.wav', 'test_ta_s1', VidTimeManager())
        self.assertEqual(1, len(result))
        self.assertEqual(6, result[0]['startframe'])
        self.assertEqual(result[0]['endframe'], result[0]['startframe'] + result[0]['frames']-1)

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta4.0.0.wav', 'test_ta_s2', VidTimeManager())
        self.assertEqual(1, len(result))
        self.assertEqual(6, result[0]['startframe'])
        self.assertEqual(result[0]['endframe'], result[0]['startframe'] + result[0]['frames']-1)

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta5.0.0.wav', 'test_ta_s3', VidTimeManager(),
                                                 arguments={'Copy Stream':'right'})
        self.assertEqual(1, len(result))
        self.assertEqual(6, result[0]['startframe'])
        self.assertEqual(result[0]['endframe'], result[0]['startframe'] + result[0]['frames']-1)


    def tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)


if __name__ == '__main__':
    unittest.main()
