import os
import unittest

import numpy as np
from maskgen import video_tools, tool_set
from maskgen.ffmpeg_api import get_meta_from_video
from maskgen.ffmpeg_api import run_ffmpeg
from mock import patch, Mock
from test_support import TestSupport


def cropForTest(frame, no):
    return frame[100:-100, 100:-100, :]


def rotateForTest(frame, no):
    return np.rotate(frame, -1)


def noiseForTest(frame, no):
    if no < 20 or no > 80:
        return frame
    result = np.round(np.random.normal(0, 2, frame.shape))
    return frame + result.astype('uint8')


def sameForTest(frame, no):
    return frame


def changeForTest(frame, no):
    if no >= 20 and no < 40:
        return np.random.randint(255, size=(1090, 1920, 3)).astype('uint8')
    return frame


def addForTest(frame, no):
    if no != 20:
        return frame
    return [frame if i == 0 else np.random.randint(255, size=(1090, 1920, 3)).astype('uint8') for i in range(20)]


def addNoise(frames, no):
    import random
    import struct
    import ctypes
    b = ctypes.create_string_buffer(len(frames))
    buffer_position = 0
    for i in range(0, len(frames), 2):
        value = struct.unpack('h', frames[i:i + 2])[0]
        position = no + buffer_position
        if (position >= 24 and position <= 64) or (position >= 192 and position <= 240):
            value = random.randint(-32767, 32767)
        struct.pack_into('h', b, buffer_position, value)
        buffer_position += 2
    return b


def sampleFrames(frames, no):
    import struct
    import ctypes
    if no < 1024:
        b = ctypes.create_string_buffer(192 - 24)
    else:
        return None
    buffer_position = 0
    read_position = 0
    for i in range(0, len(frames), 2):
        value = struct.unpack('h', frames[i:i + 2])[0]
        position = no + read_position
        read_position += 2
        if position < 24 or position >= 192:
            continue
        struct.pack_into('h', b, buffer_position, value)
        buffer_position += 2
    return b


def singleChannelSample(filename, outfilname, skip=0):
    import wave
    fone = wave.open(filename, 'rb')
    countone = fone.getnframes()
    ftwo = wave.open(outfilname, 'wb')
    ftwo.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
    toRead = min([1024, countone])
    framesone = fone.readframes(toRead)
    int_frames = np.fromstring(framesone, 'Int16')[6+skip:48+skip:2]
    ftwo.writeframesraw(int_frames.tobytes())
    fone.close()
    ftwo.close()


def augmentAudio(filename, outfilname, augmentFunc):
    import wave
    fone = wave.open(filename, 'rb')
    countone = fone.getnframes()
    onechannels = fone.getnchannels()
    onewidth = fone.getsampwidth()
    ftwo = wave.open(outfilname, 'wb')
    ftwo.setparams(fone.getparams())
    position = 0
    while True:
        toRead = min([1024, countone])
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


def deleteAudio(filename, outfilname, pos, length):
    import wave
    import struct
    import random
    fone = wave.open(filename, 'rb')
    countone = fone.getnframes()
    onechannels = fone.getnchannels()
    onewidth = fone.getsampwidth()
    ftwo = wave.open(outfilname, 'wb')
    ftwo.setparams(fone.getparams())
    pos = pos * onechannels * onewidth
    length = length * onechannels * onewidth
    framesone = fone.readframes(pos)
    ftwo.writeframes(framesone)
    fone.readframes(length)
    countone -= (pos + length)
    while countone > 0:
        toRead = min([1024, countone])
        countone -= toRead
        framesone = fone.readframes(toRead)
        ftwo.writeframes(framesone)
    fone.close()
    ftwo.close()

def insertAudio(filename, outfilname, pos, length):
    import wave
    import struct
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
    while countone > 0:
        toRead = min([1024, countone])
        countone -= toRead
        framesone = fone.readframes(toRead)
        position += toRead
        if length > 0 and position > pos:
            ftwo.writeframes(framesone[0:pos])
            while (length > 0):
                value = random.randint(-32767, 32767)
                packed_value = struct.pack('h', value)
                ftwo.writeframesraw(packed_value)
                length -= 1
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

    def _init_write_zip_file(self, name, amount, fps):
        writer = tool_set.ZipWriter(name, fps)
        amount = int(amount)
        for i in range(amount):
            mask = np.random.randint(255, size=(1090, 1920)).astype('uint8')
            writer.write(mask)
        writer.release()
        self.filesToKill.append(writer.filename)
        return writer.filename

    def _init_write_file(self, name, start_time, start_position, amount, fps, mask_set=None, maskonly=False):
        writer = tool_set.GrayBlockWriter(name, fps)
        amount = int(amount)
        increment = 1000 / float(fps)
        count = start_position
        for i in range(amount):
            if maskonly:
                mask = np.random.randint(2, size=(1090, 1920)).astype('uint8') * 255
            else:
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
            if video_tools.get_file_from_segment(segment) is not None:
                self.filesToKill.append(video_tools.get_file_from_segment(segment))

    def _init_write_video_file(self, name, alter_funcs):
        try:
            files = []
            writer_main = tool_set.GrayFrameWriter(name, 30 / 1.0,
                                                   preferences={'vid_suffix': 'avi', 'vid_codec': 'raw'})
            rate = 1 / 30.0
            main_count = 0
            counters_for_all = [0 for i in alter_funcs]
            writers = [tool_set.GrayFrameWriter(name + str(func).split()[1], 30 / 1.0,
                                                preferences={'vid_suffix': 'avi', 'vid_codec': 'raw'}) for func in
                       alter_funcs]
            for i in range(100):
                mask = np.random.randint(255, size=(1090, 1920, 3)).astype('uint8')
                writer_main.write(mask, main_count,  main_count * rate)
                nextcounts = []
                for writer, func, counter in zip(writers, alter_funcs, counters_for_all):
                    result = func(mask, i + 1)
                    if type(result) == list:
                        for item in result:
                            writer.write(item, counter, counter * rate)
                            counter += 1
                        nextcounts.append(counter)
                    else:
                        writer.write(result, counter, counter * rate)
                        nextcounts.append(counter + 1)
                counters_for_all = nextcounts
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
        locator = video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov'))
        duration = video_tools.get_duration(locator)
        self.assertTrue(abs(duration - expected) < 1)
        duration = video_tools.get_duration(locator, audio=True)
        self.assertTrue(abs(duration - expected) < 2)
        with patch('maskgen.mask_rules.BuildState', spec=locator) as mock_locator:
            mock_locator.get_frame_attribute = Mock(return_value=None)
            mock_locator.get_filename = locator.get_filename
            mock_locator.get_meta = locator.get_meta
            duration = video_tools.get_duration(mock_locator)
            self.assertTrue(abs(duration - expected) < 1)

    def test_frame_rate(self):
        locator = video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov'))
        rate = video_tools.get_frame_rate(locator)
        self.assertTrue(abs(rate - 28.25) < 0.1)
        rate = video_tools.get_frame_rate(locator, audio=True)
        self.assertTrue(abs(rate - 44100) < 1)

    def test_meta(self):
        meta, frames = get_meta_from_video(self.locateFile('tests/videos/sample1.mov'), with_frames=True)
        self.assertEqual(803, len(frames[0]))
        self.assertEqual(2557, len(frames[1]))
        meta, frames = get_meta_from_video(self.locateFile('tests/videos/sample1.mov'), show_streams=True)
        self.assertEqual('yuv420p', meta[0]['pix_fmt'])
        self.assertEqual('audio', meta[1]['codec_type'])

    def test_frame_count(self):


        #result = video_tools.get_frame_count(self.locateFile('tests/videos/fb1afd9b551cde13b6e011a201e42ae7.mts'), (2010, 0), None)
        #self.assertEqual(2356, video_tools.get_frames_from_segment(result))
        #self.assertEqual(2385, video_tools.get_end_frame_from_segment(result))
        #self.assertEqual(80579, int(video_tools.get_end_time_from_segment(result)))
        #self.assertEqual(2001.0, video_tools.get_start_time_from_segment(result))
        #self.assertEqual(30, video_tools.get_start_frame_from_segment(result))

        #result = video_tools.get_frame_count(self.locateFile('tests/videos/fb1afd9b551cde13b6e011a201e42ae7.mts'), (0, 21), (0, 593))
        ##self.assertEqual(573, video_tools.get_frames_from_segment(result))
        #self.assertEqual(593, video_tools.get_end_frame_from_segment(result))
        #self.assertEqual(20786, int(video_tools.get_end_time_from_segment(result)))
        #self.assertEqual(1700, int(video_tools.get_start_time_from_segment(result)))
        #self.assertEqual(21, video_tools.get_start_frame_from_segment(result))

        result = video_tools.get_frame_count('sample1_ffr.mov', (0, 21), (0, 593))
        self.assertEqual(59200.0, round(video_tools.get_end_time_from_segment(result)))
        self.assertEqual(573, video_tools.get_frames_from_segment(result))
        self.assertEqual(593, video_tools.get_end_frame_from_segment(result))
        self.assertEqual(2000.0, video_tools.get_start_time_from_segment(result))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result))

        result = video_tools.get_frame_count('sample1_ffr.mov', (2010, 0), (59200, 0))
        self.assertEqual(59200.0, round(video_tools.get_end_time_from_segment(result)))
        self.assertEqual(573, video_tools.get_frames_from_segment(result))
        self.assertEqual(593, video_tools.get_end_frame_from_segment(result))
        self.assertEqual(2000.0, video_tools.get_start_time_from_segment(result))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result))

        result = video_tools.get_frame_count('sample1_ffr.mov', (0, 21), None)
        self.assertEqual(575, video_tools.get_frames_from_segment(result))
        self.assertEqual(595, video_tools.get_end_frame_from_segment(result))
        self.assertEqual(59400.0, video_tools.get_end_time_from_segment(result))
        self.assertEqual(2000.0, video_tools.get_start_time_from_segment(result))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result))

        result = video_tools.get_frame_count('sample1_ffr.mov', (2010, 0), None)
        self.assertEqual(575, video_tools.get_frames_from_segment(result))
        self.assertEqual(595, video_tools.get_end_frame_from_segment(result))
        self.assertEqual(59400.0, video_tools.get_end_time_from_segment(result))
        self.assertEqual(2000.0, video_tools.get_start_time_from_segment(result))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result))



    def test_frame_binding_ffr(self):

        result = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator('sample1_ffr.mov'),
                                                      start_time='00:00:02.01',
                                                      end_time='00:00:59.29')
        self._add_mask_files_to_kill(result)
        self.assertEqual(59200.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual(573, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(593, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(2000.0, video_tools.get_start_time_from_segment(result[0]))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result[0]))

        result = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator('sample1_ffr.mov'),
                                                      start_time='00:00:02.01:02')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2200.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(video_tools.get_end_frame_from_segment(result[0])*100- 100, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual(23, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(573, video_tools.get_frames_from_segment(result[0]))

        result = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator('sample1_ffr.mov'),
                                                      start_time='00:00:02.01')
        self._add_mask_files_to_kill(result)
        self.assertEqual(575, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(595, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(video_tools.get_end_frame_from_segment(result[0])*100- 100, video_tools.get_end_time_from_segment(result[0]))
        self.assertEqual(2000.0, video_tools.get_start_time_from_segment(result[0]))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result[0]))

        result = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator('sample1_ffr.mov'),
                                                      start_time='23',
                                                      end_time='29')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2200.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(23, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(2800.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual(29, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(29 - 23 + 1, video_tools.get_frames_from_segment(result[0]))

        result = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator('videos/Sample2_ffr.mxf'),
                                                      start_time=21, end_time=None)  # ffr vid with 'N/A' nbframes.
        self._add_mask_files_to_kill(result)
        self.assertEqual(567.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(45000.0, round(video_tools.get_end_time_from_segment(result[0])/100)*100)
        self.assertEqual(1350, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(1350 - 21 + 1, video_tools.get_frames_from_segment(result[0]))

    def test_video_to_mask(self):
        from maskgen.tool_set import GrayFrameWriter, GrayBlockReader
        w = GrayFrameWriter('test_source',10, preferences={'vid_codec':'raw', 'vid_suffix':'avi'})
        m = np.zeros((1092,720,3),dtype='uint8');
        m[100:200,100:200,0] = 255
        for i in range(180):
            w.write(m, i/10.0, i)
        w.close()
        self.addFileToRemove(w.filename)
        sf = w.filename
        w = GrayFrameWriter('test',10, preferences={'vid_codec':'raw', 'vid_suffix':'avi'})
        m = np.zeros((1092,720,3),dtype='uint8');
        m[100:200,100:200,0] = 255
        for i in range(60):
            w.write(m, i/10.0, i)
        w.close()
        self.addFileToRemove(w.filename)
        masks = video_tools.videoMasksFromVid(w.filename,'test_mask')
        self._add_mask_files_to_kill(masks)
        hdf5filename = masks[0]['videosegment']
        r = GrayBlockReader(hdf5filename)
        m = r.read()
        c = 0
        self.assertEqual(255,m[0,0])
        self.assertEqual(0, m[101,101])
        self.assertEqual('video',video_tools.get_type_of_segment(masks[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(masks[0]))
        self.assertEqual(60, video_tools.get_end_frame_from_segment(masks[0]))
        self.assertEqual(10, video_tools.get_rate_from_segment(masks[0]))
        self.assertEqual(5900, video_tools.get_end_time_from_segment(masks[0]))
        while m is not None:
            self.assertEquals(c+2, r.current_frame())
            c += 1
            m = r.read()
            if m is not None:
                self.assertEqual(255,m[0,0])
                self.assertEqual(0, m[101,101])
        self.assertEqual(60, c)
        r.close()

        masks = video_tools.formMaskForSource(sf,w.filename,'test_mask',
                                              startTimeandFrame=(0,60),
                                              stopTimeandFrame=(0,119))
        hdf5filename = masks[0]['videosegment']
        r = GrayBlockReader(hdf5filename)
        m = r.read()
        c = 0
        self.assertEqual(255, m[0, 0])
        self.assertEqual(0, m[101, 101])
        self.assertEqual('video', video_tools.get_type_of_segment(masks[0]))
        self.assertEqual(60, video_tools.get_start_frame_from_segment(masks[0]))
        self.assertEqual(119, video_tools.get_end_frame_from_segment(masks[0]))
        self.assertEqual(10, video_tools.get_rate_from_segment(masks[0]))
        self.assertEqual(11800, int(video_tools.get_end_time_from_segment(masks[0])))
        while m is not None:
            self.assertEquals(c + 61, r.current_frame())
            c += 1
            m = r.read()
            if m is not None:
                self.assertEqual(255, m[0, 0])
                self.assertEqual(0, m[101, 101])
        self.assertEqual(60, c)

    def test_frame_binding_vfr(self):

        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')))  # Variable FR
        self._add_mask_files_to_kill(result)
        self.assertEqual(0.0, video_tools.get_start_time_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(803, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(803.0, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(59348.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual('video', video_tools.get_type_of_segment(result[0]))

        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1_slow.mov')))  # Constant FR
        self._add_mask_files_to_kill(result)
        self.assertEqual(0.0, video_tools.get_start_time_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(596, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(596, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(59500.0, video_tools.get_end_time_from_segment(result[0]))
        self.assertEqual('video', video_tools.get_type_of_segment(result[0]))

        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1_slow.mov')),
            start_time='00:00:02.01')  # Constant FR
        self._add_mask_files_to_kill(result)
        self.assertEqual(2000.0, video_tools.get_start_time_from_segment(result[0]))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(576, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(596, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(59500.0, video_tools.get_end_time_from_segment(result[0]))
        self.assertEqual('video', video_tools.get_type_of_segment(result[0]))

        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1_swap.mov')),
            start_time='00:00:02.01', end_time='00:00:59.29')  # Variable FR, swapped streams, fails to grab all frames
        self._add_mask_files_to_kill(result)
        self.assertEqual(59221.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual(779, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(801, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(23, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(1982.0, round(video_tools.get_start_time_from_segment(result[0])))

        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1_swap.mov')),
            start_time='00:00:02.01')  # Variable FR, swapped streams.
        self._add_mask_files_to_kill(result)
        self.assertEqual(1982.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(23, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(803 - 23 + 1, video_tools.get_frames_from_segment(result[0]))
        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')), start_time='00:00:02.01')
        self._add_mask_files_to_kill(result)
        self.assertEqual(1982.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(23, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(803 - 23 + 1, video_tools.get_frames_from_segment(result[0]))
        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')), start_time='00:00:02.01:02')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2123.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(24, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(780, video_tools.get_frames_from_segment(result[0]))
        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')), start_time='00:00:02.01',
            end_time='00:00:04.01')
        self._add_mask_files_to_kill(result)
        self.assertEqual(1982.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(23, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(3965.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual(47, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(47 - 23 + 1, video_tools.get_frames_from_segment(result[0]))
        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')), start_time='23',
            end_time='29')
        self._add_mask_files_to_kill(result)
        self.assertEqual(1982.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(23, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(2548.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual(29, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(29 - 23 + 1, video_tools.get_frames_from_segment(result[0]))
        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')), start_time='29',
            end_time='55')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2548.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(29, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(4532.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual(55, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(55 - 29 + 1, video_tools.get_frames_from_segment(result[0]))
        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')), start_time='29')
        self._add_mask_files_to_kill(result)
        self.assertEqual(2548.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(29, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(59348.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual(803, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(803 - 29 + 1, video_tools.get_frames_from_segment(result[0]))
        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')),
            media_types=['audio'])
        self._add_mask_files_to_kill(result)
        self.assertEqual(0.0, video_tools.get_start_time_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(2617262, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(2617262, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(59348.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual('audio', video_tools.get_type_of_segment(result[0]))
        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')),
            start_time='1',
            media_types=['video'])
        self._add_mask_files_to_kill(result)
        self.assertEqual(0.0, video_tools.get_start_time_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(803, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(803, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(59348.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual('video', video_tools.get_type_of_segment(result[0]))
        result = video_tools.getMaskSetForEntireVideo(
            video_tools.FileMetaDataLocator(self.locateFile('tests/videos/sample1.mov')), start_time='00:00:02.01',
            end_time='00:00:04',
            media_types=['audio'])
        self._add_mask_files_to_kill(result)
        self.assertEqual(2010.0, round(video_tools.get_start_time_from_segment(result[0])))
        self.assertEqual(88641, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(4000.0, round(video_tools.get_end_time_from_segment(result[0])))
        self.assertEqual(176400, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(176400 - 88641 + 1, video_tools.get_frames_from_segment(result[0]))

    def test_extract_mask(self):
        amount = 30
        fileOne = self._init_write_file('test_ts_em1', 2500, 75, 30, 30, maskonly=True)
        fileTwo = self._init_write_file('test_ts_em2', 4100, 123, 27, 30, maskonly=True)
        sets = []
        change = video_tools.create_segment(
            starttime=2500,
            startframe=75,
            endtime=3500,
            endframe=75 + amount - 1,
            frames=amount,
            rate=30,
            videosegment=fileOne,
            type='video')
        sets.append(change)
        change = video_tools.create_segment(
            starttime=4100,
            startframe=123,
            endtime=5000,
            endframe=149,
            frames=int(27),
            rate=30,
            videosegment=fileTwo,
            type='video')
        sets.append(change)

        reader = tool_set.GrayBlockReader(fileTwo)
        c = 0
        while c < 3:
            expect_mask = reader.read()
            c += 1
        reader.close()

        mask = video_tools.extractMask(sets, 125)

        self.assertTrue(np.all(mask == expect_mask))

    def test_formMaskDiffForImage(self):
        from maskgen.image_wrap import ImageWrapper
        fileOne = self._init_write_zip_file('test_ts_fmdfi.png.zip', 20, 30)
        test_image = np.random.randint(255, size=(1090, 1920)).astype('uint8')
        masks = video_tools.formMaskDiffForImage(fileOne, ImageWrapper(test_image), 'test_ts_fmdfi', 'op')
        self.assertEqual(1, len(masks))
        mask = masks[0]
        self.assertEquals(20, video_tools.get_frames_from_segment(mask))
        self.assertEquals(1, video_tools.get_start_frame_from_segment(mask))
        self.assertEquals(20, video_tools.get_end_frame_from_segment(mask))
        self.assertEquals(0, video_tools.get_start_time_from_segment(mask))
        self.assertEquals(666, int(video_tools.get_end_time_from_segment(mask)))
        reader = tool_set.GrayBlockReader(video_tools.get_file_from_segment(mask))
        count = 0
        while True:
            diff_mask = reader.read()
            if diff_mask is None:
                break
            self.assertTrue(np.sum(255-diff_mask) > 0)
            count += 1
        self.assertEqual(20, count)

    def test_inverse_intersection_for_mask(self):
        amount = 30
        fileOne = self._init_write_file('test_ts_em1', 2500, 75, 30, 30, maskonly=True)
        sets = []
        change = video_tools.create_segment(
            starttime=2500,
            startframe=75,
            endtime=3500,
            endframe=75 + amount - 1,
            frames=amount,
            rate=30,
            videosegment=fileOne,
            type='video')
        sets.append(change)

        test_mask = np.random.randint(2, size=(1090, 1920)).astype('uint8') * 255

        new_sets = video_tools.inverse_intersection_for_mask(test_mask, sets)

        reader = tool_set.GrayBlockReader(video_tools.get_file_from_segment(new_sets[0]))
        while True:
            expect_mask = reader.read()
            if expect_mask is None:
                break
            self.assertTrue(np.all((test_mask.astype('int') - 255-expect_mask.astype('int') <= 0)))

    def test_remove_intersection(self):
        setOne = []
        maskitem = video_tools.create_segment(
            starttime=900,
            startframe=10,
            endtime=2900,
            endframe=30,
            frames=21,
            rate=10,
            type='video')
        setOne.append(maskitem)
        maskitem = video_tools.create_segment(
            starttime=4900,
            startframe=50,
            endtime=6900,
            endframe=70,
            frames=21,
            rate=10,
            type='video')
        setOne.append(maskitem)

        setTwo = []
        maskitem = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=500,
            endframe=6,
            frames=6,
            rate=10,
            type='video')
        setTwo.append(maskitem)
        maskitem = video_tools.create_segment(
            starttime=800,
            startframe=9,
            endtime=1400,
            endframe=15,
            frames=7,
            rate=10,
            type='video')
        setTwo.append(maskitem)
        maskitem = video_tools.create_segment(
            starttime=2400,
            startframe=25,
            endtime=3400,
            endframe=35,
            frames=11,
            rate=10,
            type='video')
        setTwo.append(maskitem)
        maskitem = video_tools.create_segment(
            starttime=3200,
            startframe=44,
            endtime=4600,
            endframe=47,
            frames=4,
            rate=10,
            type='video')
        setTwo.append(maskitem)
        maskitem = video_tools.create_segment(
            starttime=8900,
            startframe=90,
            endtime=9400,
            endframe=95,
            frames=6,
            rate=10,
            type='video')
        setTwo.append(maskitem)

        finalsets = video_tools.removeIntersectionOfMaskSets(setOne, setTwo)
        self.assertEquals(6, len(finalsets))
        self.assertEqual([
            {'endframe': 6, 'rate': 10, 'starttime': 0, 'frames': 6, 'startframe': 1, 'endtime': 500,
             'type': 'video', 'error':0},
            {'endframe': 9, 'rate': 10, 'starttime': 800, 'frames': 1, 'startframe': 9, 'endtime': 800.0,
             'type': 'video', 'error':0},
            {'endframe': 30, 'rate': 10, 'starttime': 900, 'frames': 21, 'startframe': 10, 'endtime': 2900,
             'type': 'video', 'error':0},
            {'endframe': 47, 'rate': 10, 'starttime': 3200, 'frames': 4, 'startframe': 44, 'endtime': 4600,
             'type': 'video', 'error':0},
            {'endframe': 70, 'rate': 10, 'starttime': 4900, 'frames': 21, 'startframe': 50, 'endtime': 6900,
             'type': 'video', 'error':0},
            {'endframe': 95, 'rate': 10, 'starttime': 8900, 'frames': 6, 'startframe': 90, 'endtime': 9400,
             'type': 'video', 'error':0}], finalsets)

    def test_before_dropping(self):
        amount = 30
        fileOne = self._init_write_file('test_ts_bd1', 2500, 75, 30, 30)
        fileTwo = self._init_write_file('test_ts_bd2', 4100, 123, 27, 30)
        sets = []
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=1000,
            endframe=30,
            frames=30,
            rate=30,
            error=1.1,
            type='video')
        sets.append(change)
        change = video_tools.create_segment(
            starttime=2500,
            startframe=75,
            endtime=3500,
            endframe=75 + amount - 1,
            frames=amount,
            rate=30,
            error=1.2,
            videosegment=fileOne,
            type='video')
        sets.append(change)
        change = video_tools.create_segment(
            starttime=4100,
            startframe=123,
            endtime=5000,
            endframe=149,
            frames=int(27),
            rate=30,
            error=1.3,
            videosegment=fileTwo,
            type='video')
        sets.append(change)

        result = video_tools.dropFramesFromMask([video_tools.create_segment(**{
            'startframe': 90,
            'starttime': 3000,
            'endframe': 117,
            'endtime': 4000
        })], sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(3, len(result))
        self.assertEqual(15, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(89, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(96, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(122, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.3, video_tools.get_error_from_segment(result[2]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))

        result = video_tools.dropFramesFromMask([video_tools.create_segment(**{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        })], sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(3, len(result))
        self.assertEqual(15, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(63, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(77, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(96, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(122, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.3, video_tools.get_error_from_segment(result[2]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))

        result = video_tools.dropFramesFromMask([video_tools.create_segment(**{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        })], sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(4, len(result))
        self.assertEqual(12, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(86, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(12, video_tools.get_frames_from_segment(result[2]))
        self.assertEqual(87, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(98, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(117, video_tools.get_start_frame_from_segment(result[3]))
        self.assertEqual(143, video_tools.get_end_frame_from_segment(result[3]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[2]))
        self.assertEqual(1.3, video_tools.get_error_from_segment(result[3]))

        result = video_tools.dropFramesFromMask([video_tools.create_segment(**{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        })], sets, keepTime=True)
        self._add_mask_files_to_kill(result)
        self.assertEqual(4, len(result))
        self.assertEqual(12, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(12, video_tools.get_frames_from_segment(result[2]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(86, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(93, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(104, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(123, video_tools.get_start_frame_from_segment(result[3]))
        self.assertEqual(149, video_tools.get_end_frame_from_segment(result[3]))
        self.assertEqual(4, len(result))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[2]))
        self.assertEqual(1.3, video_tools.get_error_from_segment(result[3]))

        result = video_tools.dropFramesFromMask([video_tools.create_segment(**{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        })], sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(2, len(result))
        self.assertEqual(12, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(12, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(31, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(57, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.3, video_tools.get_error_from_segment(result[1]))

        result = video_tools.dropFramesFromMask([video_tools.create_segment(**{
            'startframe': 93,
            'starttime': 3100
        })], sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(2, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(30, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(92, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))

        result = video_tools.dropFramesFromMask([video_tools.create_segment(**{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        })], sets, keepTime=True)
        self._add_mask_files_to_kill(result)
        self.assertEqual(2, len(result))
        self.assertEqual(12, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(93, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(104, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(123, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(149, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.3, video_tools.get_error_from_segment(result[1]))

        result = video_tools.dropFramesFromMask([video_tools.create_segment(**{
            'startframe': 93,
            'starttime': 3100,
        })], sets, keepTime=True)
        self._add_mask_files_to_kill(result)
        self.assertEqual(2, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(30, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(18, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(92, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))

    def test_before_dropping_nomask(self):
        amount = 30
        sets = []
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=1000,
            endframe=30,
            frames=30,
            rate=30,
            type='video',
            error=1.1)
        sets.append(change)
        change = video_tools.create_segment(
            starttime=2500,
            startframe=75,
            endtime=3500,
            endframe=75 + amount - 1,
            frames=amount,
            rate=30,
            type='video',
            error=1.2)
        sets.append(change)
        change = video_tools.create_segment(
            starttime=4100,
            startframe=123,
            endtime=5000,
            endframe=149,
            frames=int(27),
            rate=30,
            type='video',
            error=1.3)
        sets.append(change)
        result = video_tools.dropFramesWithoutMask([video_tools.create_segment(**{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 92,
            'endtime': 3100
        })], sets)
        self.assertEqual(4, len(result))
        self.assertEqual(12, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(86, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(12, video_tools.get_frames_from_segment(result[2]))
        self.assertEqual(87, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(98, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(117, video_tools.get_start_frame_from_segment(result[3]))
        self.assertEqual(143, video_tools.get_end_frame_from_segment(result[3]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[2]))
        self.assertEqual(1.3, video_tools.get_error_from_segment(result[3]))

        result = video_tools.dropFramesWithoutMask([video_tools.create_segment(**{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        })], sets)
        self.assertEqual(3, len(result))
        self.assertEqual(14, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(63, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(76, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(95, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(121, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))
        self.assertEqual(1.3, video_tools.get_error_from_segment(result[2]))

        result = video_tools.dropFramesWithoutMask([video_tools.create_segment(**{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        })], sets, keepTime=True)
        self.assertEqual(4, len(result))
        self.assertEqual(12, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(11, video_tools.get_frames_from_segment(result[2]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(86, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(94, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(104, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(123, video_tools.get_start_frame_from_segment(result[3]))
        self.assertEqual(149, video_tools.get_end_frame_from_segment(result[3]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[2]))
        self.assertEqual(1.3, video_tools.get_error_from_segment(result[3]))

        result = video_tools.dropFramesWithoutMask([video_tools.create_segment(**{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        })], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(11, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(11, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(30, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(56, video_tools.get_end_frame_from_segment(result[1]))

        result = video_tools.dropFramesWithoutMask([video_tools.create_segment(**{
            'startframe': 93,
            'starttime': 3100
        })], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(30, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(18, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(92, video_tools.get_end_frame_from_segment(result[1]))

        result = video_tools.dropFramesWithoutMask([video_tools.create_segment(**{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        })], sets, keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(11, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(94, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(104, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(123, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(149, video_tools.get_end_frame_from_segment(result[1]))

        result = video_tools.dropFramesWithoutMask([video_tools.create_segment(**{
            'startframe': 93,
            'starttime': 3100
        })], sets, keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(30, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(18, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(92, video_tools.get_end_frame_from_segment(result[1]))

    def after_general_all(self, sets, func):
        result = func(
            [video_tools.create_segment(**{
                'startframe': 180,
                'starttime': 6000,
                'endframe': 210,
                'endtime': 7000
            })], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))
        self._add_mask_files_to_kill(result)

        result = func([video_tools.create_segment(**{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        })], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(103, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))
        self._add_mask_files_to_kill(result)

        result = func([video_tools.create_segment(**{
            'startframe': 81,
            'starttime': 2700,
            'endframe': 111,
            'endtime': 3700
        })], sets)
        self.assertEqual(3, len(result))
        self.assertEqual(6, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(24, video_tools.get_frames_from_segment(result[2]))
        self.assertEqual(112, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(135, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[2]))
        self._add_mask_files_to_kill(result)

        result = func([video_tools.create_segment(**{
            'startframe': 1,
            'starttime': 0,
            'endframe': 63,
            'endtime': 2100
        })], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(64, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(93, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(138, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(167, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))
        self._add_mask_files_to_kill(result)

    def test_cutCompare(self):

        source = 'sample1_ffr.mov'
        run_ffmpeg(['-y', '-i', source, '-ss', '00:00:00.00', '-t', '10', 'part1.mov'])
        run_ffmpeg(['-y', '-i', source, '-ss', '00:00:12.00', 'part2.mov'])
        run_ffmpeg(['-y', '-i', 'part1.mov', '-i', 'part2.mov', '-filter_complex',
                    '[0:v][0:a][1:v][1:a] concat=n=2:v=1:a=1 [outv] [outa]',
                    '-map', '[outv]', '-map', '[outa]', 'sample1_cut_full.mov'])
        self.filesToKill.append('part1.mov')
        self.filesToKill.append('part2.mov')
        self.filesToKill.append('sample1_cut_full.mov')
        orig_vid = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator(source))
        cut_vid = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator('sample1_cut_full.mov'))
        diff_in_frames = video_tools.get_frames_from_segment(orig_vid[0]) - video_tools.get_frames_from_segment(
            cut_vid[0])
        maskSet, errors = video_tools.cutCompare(source, 'sample1_cut_full.mov', 'sample1',
                                                 tool_set.VidTimeManager(startTimeandFrame=(10000, 0),
                                                                         stopTimeandFrame=(12000, 0)))
        videoSet = [mask for mask in maskSet if video_tools.get_type_of_segment(mask) == 'video']
        self.assertEquals(diff_in_frames, video_tools.get_frames_from_segment(videoSet[0]))
        audioSet = [mask for mask in maskSet if video_tools.get_type_of_segment(mask) == 'audio']
        print(maskSet[0])
        print(audioSet[0])
        self.assertEqual(1, len(audioSet))
        self.assertEqual(865, int(round(video_tools.get_frames_from_segment(audioSet[0]))/100))
        self.assertEqual(44, int(video_tools.get_start_frame_from_segment(audioSet[0])/10000))
        self.assertEquals(video_tools.get_start_time_from_segment(audioSet[0]),
                          video_tools.get_start_time_from_segment(maskSet[0]))
        self.assertTrue(0.2 > abs(
            video_tools.get_end_time_from_segment(audioSet[0]) / 1000.0 - video_tools.get_end_time_from_segment(
                maskSet[0]) / 1000.0))
        self.assertEqual(44100.0, video_tools.get_rate_from_segment(audioSet[0]))
        videoSet = [mask for mask in maskSet if video_tools.get_type_of_segment(mask) == 'video']
        self.assertEqual(20, video_tools.get_frames_from_segment(videoSet[0]))
        self.assertEqual(101, video_tools.get_start_frame_from_segment(videoSet[0]))
        self.assertEqual(120, video_tools.get_end_frame_from_segment(videoSet[0]))

    def test_align_streams_meta(self):
        meta_and_frames = ([{'codec_type': 'video'}, {'codec_type': 'audio', 'channel_layout': 'mono'}],  # normal
                           [[{'key_frame': 1}], [{'channels': 1}]])
        meta, frames = video_tools._align_streams_meta(meta_and_frames, excludeAudio=False)
        self.assertTrue(len(meta) == 2 and meta['video']['codec_type'] == 'video')
        self.assertTrue(len(frames) == 2 and frames['video'][0]['key_frame'] == 1)
        meta, frames = video_tools._align_streams_meta(meta_and_frames, excludeAudio=True)  # excludeAudio
        self.assertTrue(len(meta) == 1 and len(frames) == 1)
        meta_and_frames = ([{'codec_type': 'video'}, {'codec_type': 'audio', 'channel_layout': 'mono'},
                            # multiple streams of similar type
                            {'codec_type': 'audio', 'channel_layout': 'mono'}], [])
        meta, frames = video_tools._align_streams_meta(meta_and_frames, excludeAudio=False)
        self.assertTrue(len(meta) == 3 and meta.has_key('mono1'))

        """
        VFR NOT WORKING
        source = self.locateFile('tests/videos/sample1.mov')
        orig_vid = video_tools.getMaskSetForEntireVideo(source)
        video_tools.runffmpeg(
            ['-y', '-i', source, '-ss', '00:00:00.00', '-t', '10', '-r', str(video_tools.get_rate_from_segment(orig_vid[0])), 'part1.mov'])
        video_tools.runffmpeg(
            ['-y', '-i', source, '-ss', '00:00:12.00', '-r', str(video_tools.get_rate_from_segment(orig_vid[0])), 'part2.mov'])
        video_tools.runffmpeg(['-y','-i', 'part1.mov', '-i','part2.mov','-filter_complex',
                               '[0:v][0:a][1:v][1:a] concat=n=2:v=1:a=1 [outv] [outa]',
                               '-map','[outv]','-map','[outa]','-r', str(video_tools.get_rate_from_segment(orig_vid[0])),'sample2_cut_full.mov'])
        self.filesToKill.append('part1.mov')
        self.filesToKill.append('part2.mov')
        self.filesToKill.append('sample2_cut_full.mov')
        cut_vid = video_tools.getMaskSetForEntireVideo('sample2_cut_full.mov')
        diff_in_frames = video_tools.get_frames_from_segment(orig_vid[0]) - video_tools.get_frames_from_segment(cut_vid[0])
        maskSet, errors = video_tools.cutCompare(source,'sample2_cut_full.mov','sample1',tool_set.VidTimeManager(startTimeandFrame=(10000,0),
                                                                                       stopTimeandFrame=(11900,0)))
        audioSet = [mask for mask in  maskSet if type=='audio']
        videoSet = [mask for mask in maskSet if type== 'video']
        self.assertEquals(diff_in_frames, video_tools.get_frames_from_segment(videoSet[0]))
        print(maskSet[0])
        print(audioSet[0])
        self.assertEqual(1, len(audioSet))
        self.assertEqual(85526, video_tools.get_frames_from_segment(audioSet[0]))
        self.assertEqual(440339, video_tools.get_start_frame_from_segment(audioSet[0]))
        self.assertEqual(440339+85526-1, video_tools.get_end_frame_from_segment(audioSet[0]))
        self.assertEquals(video_tools.get_start_time_from_segment(audioSet[0]),video_tools.get_start_time_from_segment(maskSet[0]))
        self.assertTrue(0.2 > abs(video_tools.get_end_time_from_segment(audioSet[0])/1000.0-video_tools.get_end_time_from_segment(maskSet[0])/1000.0))
        self.assertEqual(44100.0, video_tools.get_rate_from_segment(audioSet[0]))
        """

    def test_cut(self):
        sets = []
        change = video_tools.create_segment(
            starttime=3078.1,
            startframe=94,
            endtime=3111.4,
            endframe=95,
            frames=2,
            rate=30,
            type='video')
        sets.append(change)
        change = video_tools.create_segment(
            starttime=3078.1,
            startframe=94,
            endtime=3263.4,
            endframe=99,
            frames=5,
            rate=30,
            type='video')
        result = video_tools.insertFrames([change], sets)
        self.assertEqual(100, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(101, video_tools.get_end_frame_from_segment(result[0]))
        self.assertAlmostEqual(3296.73, video_tools.get_start_time_from_segment(result[0]), places=2)
        self.assertAlmostEqual(3330.03, video_tools.get_end_time_from_segment(result[0]), places=2)
        sets = []
        change = video_tools.create_segment(
            starttime=3078.1,
            startframe=94,
            endtime=3111.4,
            endframe=95,
            frames=2,
            rate=30,
            type='video')
        sets.append(change)
        change = video_tools.create_segment(
            starttime=3296.7,
            startframe=96,
            endtime=3296.7,
            endframe=96,
            frames=2,
            rate=30,
            type='video')
        sets.append(change)
        change = video_tools.create_segment(
            starttime=3111.4,
            startframe=95,
            endtime=3111.4,
            endframe=95,
            frames=1,
            rate=30,
            type='video')
        result = video_tools.insertFrames([change], sets)
        self.assertEqual(94, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(94, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(96, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(96, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(97, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(97, video_tools.get_end_frame_from_segment(result[2]))
        self.assertAlmostEqual(3144.73, video_tools.get_start_time_from_segment(result[1]), places=2)
        self.assertAlmostEqual(3144.73, video_tools.get_end_time_from_segment(result[1]), places=2)
        self.assertAlmostEqual(3330.03, video_tools.get_start_time_from_segment(result[2]), places=2)
        self.assertAlmostEqual(3330.03, video_tools.get_end_time_from_segment(result[2]), places=2)

        sets = []
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=3111.4,
            endframe=95,
            frames=2,
            rate=30,
            type='video')
        sets.append(change)
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=-33.333,
            endframe=0,
            frames=0,
            rate=30,
            type='video')
        result = video_tools.insertFrames([change], sets)
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(95, video_tools.get_end_frame_from_segment(result[0]))
        self.assertAlmostEqual(3111.40, video_tools.get_end_time_from_segment(result[0]), places=2)
        self.assertAlmostEqual(0, video_tools.get_start_time_from_segment(result[0]), places=2)

    def test_after_dropping(self):
        amount = 30
        fileOne = self._init_write_file('test_ts_bd1', 0, 1, 30, 30)
        fileTwo = self._init_write_file('test_ts_bd2', 2500, 75, 30, 30)
        sets = []
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=1000,
            endframe=amount,
            frames=amount,
            rate=30,
            type='video',
            error=1.1,
            videosegment=fileOne)
        sets.append(change)
        change = video_tools.create_segment(
            starttime=2500,
            startframe=75,
            endtime=3500,
            endframe=75 + amount - 1,
            frames=amount,
            rate=30,
            error=1.2,
            type='video',
            videosegment=fileTwo)
        sets.append(change)
        self.after_general_all(sets, video_tools.insertFrames)

    def test_resize(self):
        fileOne = self._init_write_file('test_td_rs', 0, 1, 30, 30)
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=1000,
            endframe=30,
            frames=30,
            rate=29,
            type='video',
            error=1.1,
            videosegment=fileOne)
        result = video_tools.resizeMask([change], (1000, 1720))
        self.assertEqual(1, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))

    def test_crop(self):
        fileOne = self._init_write_file('test_td_rs', 0, 1, 30, 30)
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=1000,
            endframe=30,
            frames=30,
            rate=29,
            type='video',
            error=1.1,
            videosegment=fileOne)
        result = video_tools.cropMask([change], (100, 100, 900, 1120))
        self.assertEqual(1, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self._add_mask_files_to_kill(result)
        result = video_tools.insertMask([change], (100, 100, 900, 1120), (1090, 1920))
        self.assertEqual(1, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self._add_mask_files_to_kill(result)

    def test_rotate(self):
        fileOne = self._init_write_file('test_td_rs', 0, 1, 30, 30)
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=1000,
            endframe=30,
            frames=30,
            rate=29,
            error=1.1,
            type='video',
            videosegment=fileOne)
        result = video_tools.rotateMask(-90, [change], expectedDims=(1920, 1090))
        self.assertEqual(1, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self._add_mask_files_to_kill(result)

    def test_reverse(self):

        result = video_tools.reverseMasks([video_tools.create_segment(**{
            'startframe': 1,
            'starttime': 0,
            'endframe': 130,
            'error': 1.1,
            'endtime': 4333,
            'type': 'video'
        })], [video_tools.create_segment(**{'starttime': 0,
                                            'startframe': 0,
                                            'endframe': 130,
                                            'error': 1.1,
                                            'endtime': 4333,
                                            'type': 'video'})])
        self.assertEqual(1, len(result))
        self.assertEqual(4333, video_tools.get_end_time_from_segment(result[0]))
        self.assertEqual(130, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))

        amount = 30
        fileOne = self._init_write_file('test_tr1', 2500, 75, 30, 30)
        fileTwo = self._init_write_file('test_tr2', 4100, 123, 30, 27)
        sets = []
        change = video_tools.create_segment(
            starttime=2500,
            startframe=75,
            endtime=3500,
            endframe=75 + amount - 1,
            frames=amount,
            rate=30,
            videosegment=fileOne,
            type='video',
            error=1.1)
        sets.append(change)
        change = video_tools.create_segment(
            starttime=4100,
            startframe=123,
            endtime=5000,
            endframe=149,
            frames=int(27),
            rate=30,
            videosegment=fileTwo,
            type='video',
            error=1.2)
        sets.append(change)

        result = video_tools.reverseMasks([video_tools.create_segment(**{
            'startframe': 90,
            'starttime': 3000,
            'endframe': 130,
            'endtime': 4333,
            'type': 'video'
        })], sets)
        self.assertEqual(4, len(result))
        self.assertEqual(15, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(89, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(15, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(130, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(116, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(8, video_tools.get_frames_from_segment(result[2]))
        self.assertEqual(97, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(90, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(19, video_tools.get_frames_from_segment(result[3]))
        self.assertEqual(149, video_tools.get_end_frame_from_segment(result[3]))
        self.assertEqual(131, video_tools.get_start_frame_from_segment(result[3]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[1]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[2]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[3]))
        self._add_mask_files_to_kill(result)

        reader_orig = tool_set.GrayBlockReader(video_tools.get_file_from_segment(sets[0]))
        reader_new = tool_set.GrayBlockReader(video_tools.get_file_from_segment(result[0]))
        c = 0
        while c < 16:
            orig_mask = reader_orig.read()
            if orig_mask is None:
                break
            new_mask = reader_new.read()
            if new_mask is None:
                break
            is_equal = np.all(orig_mask == new_mask)
            c+=1
            self.assertTrue(is_equal)
        reader_new.close()
        reader_new = tool_set.GrayBlockReader(video_tools.get_file_from_segment(result[1]))
        reader_new.close()
        reader_new = tool_set.GrayBlockReader(video_tools.get_file_from_segment(result[2]))
        reader_new.close()
        reader_new = tool_set.GrayBlockReader(video_tools.get_file_from_segment(result[3]))
        reader_new.close()
        reader_orig.close()

        for item in sets:
            item.pop('videosegment')
        result = video_tools.reverseMasks([video_tools.create_segment(**{
            'startframe': 90,
            'starttime': 3000,
            'endframe': 130,
            'endtime': 4333,
            'type': 'video'
        })], sets)
        self.assertEqual(4, len(result))
        self.assertEqual(15, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(89, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(15, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(130, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(116, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(8, video_tools.get_frames_from_segment(result[2]))
        self.assertEqual(97, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(90, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(19, video_tools.get_frames_from_segment(result[3]))
        self.assertEqual(149, video_tools.get_end_frame_from_segment(result[3]))
        self.assertEqual(131, video_tools.get_start_frame_from_segment(result[3]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[1]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[2]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[3]))
        self._add_mask_files_to_kill(result)

    def test_invertVideoMasks(self):
        start_set = []
        fileOne = self._init_write_file('test_iv_rs', 0, 1, 30, 30, mask_set=start_set)
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=1000,
            endframe=30,
            frames=30,
            rate=29,
            error=1.1,
            type='video',
            videosegment=fileOne)
        result = video_tools.invertVideoMasks([change], 'x', 'y')
        self.assertEqual(1, len(result))
        self.assertEqual(30, video_tools.get_frames_from_segment(result[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        reader = tool_set.GrayBlockReader(video_tools.get_file_from_segment(result[0]))
        self._add_mask_files_to_kill(result)
        mask = reader.read()
        self.assertEqual(2, reader.current_frame())
        self.assertEqual(33, reader.current_frame_time())
        self.assertTrue(np.all(255 - mask == start_set[0]))
        reader.close()

    def test_all_mods(self):
        mod_functions = [sameForTest, cropForTest, noiseForTest, addForTest, changeForTest]
        # fileOne,modFiles = 'test_td_rs_mask_0.0.avi',['test_td_rssameForTest_mask_0.0.avi',
        #                                              'test_td_rscropForTest_mask_0.0.avi',
        #                                              'test_td_rsnoiseForTest_mask_0.0.avi',
        #                                              'test_td_rsaddForTest_mask_0.0.avi']
        fileOne, modFiles = self._init_write_video_file('test_td_rs', mod_functions)
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
                                                      arguments={'add type': 'replace'})
        self.assertEqual(1, len(result_add))
        self.assertEqual(20, video_tools.get_start_frame_from_segment(result_add[0]))
        self.assertEqual(39, video_tools.get_end_frame_from_segment(result_add[0]))
        self.assertEqual(1266, int(video_tools.get_end_time_from_segment(result_add[0])))

        result_add, errors = video_tools.formMaskDiff(fileOne,
                                                      modFiles[4],
                                                      modFiles[4],
                                                      'PasteFrames',
                                                      startSegment=None,
                                                      endSegment="39",
                                                      analysis=analysis,
                                                      alternateFunction=video_tools.pasteCompare,
                                                      arguments={'add type': 'replace'})
        self.assertEqual(1, len(result_add))
        self.assertEqual(20, video_tools.get_start_frame_from_segment(result_add[0]))
        self.assertEqual(39, video_tools.get_end_frame_from_segment(result_add[0]))
        self.assertEqual(1266, int(video_tools.get_end_time_from_segment(result_add[0])))

        result_add, errors = video_tools.formMaskDiff(fileOne,
                                                      modFiles[3],
                                                      modFiles[3],
                                                      'PasteFrames',
                                                      startSegment=None,
                                                      endSegment=None,
                                                      analysis=analysis,
                                                      alternateFunction=video_tools.pasteCompare,
                                                      arguments={'add type': 'insert'})
        self.assertEqual(1, len(result_add))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result_add[0]))
        self.assertEqual(39, video_tools.get_end_frame_from_segment(result_add[0]))
        self.assertEqual(19, video_tools.get_frames_from_segment(result_add[0]))

        result_add, errors = video_tools.formMaskDiff(fileOne,
                                                      modFiles[3],
                                                      modFiles[3],
                                                      'PasteFrames',
                                                      startSegment=None,
                                                      endSegment="39",
                                                      analysis=analysis,
                                                      alternateFunction=video_tools.pasteCompare,
                                                      arguments={'add type': 'insert'})
        self.assertEqual(1, len(result_add))
        self.assertEqual(21, video_tools.get_start_frame_from_segment(result_add[0]))
        self.assertEqual(39, video_tools.get_end_frame_from_segment(result_add[0]))
        self.assertEqual(19, video_tools.get_frames_from_segment(result_add[0]))

        result_crop, errors = video_tools.formMaskDiff(fileOne,
                                                       modFiles[1],
                                                       modFiles[1],
                                                       'TransformCrop',
                                                       startSegment=None,
                                                       endSegment=None,
                                                       analysis=analysis,
                                                       alternateFunction=video_tools.cropCompare,
                                                       arguments={})
        self.assertEqual(1, len(result_crop))
        self.assertEqual(100, video_tools.get_frames_from_segment(result_crop[0]))
        self.assertEqual(1, video_tools.get_start_frame_from_segment(result_crop[0]))
        self.assertTrue(analysis['location'].find('100, 100') > 0)
        result_noise1, errors = video_tools.formMaskDiff(fileOne,
                                                         modFiles[2],
                                                         modFiles[2],
                                                         'AddNoise',
                                                         startSegment=None,
                                                         endSegment=None,
                                                         analysis=analysis,
                                                         alternateFunction=None,
                                                         arguments={})
        self.assertTrue(len(result_noise1) >= 1)
        self.assertEqual(
            video_tools.get_end_frame_from_segment(result_noise1[0]) - video_tools.get_start_frame_from_segment(
                result_noise1[0]) + 1, video_tools.get_frames_from_segment(result_noise1[0]))
        self.assertEqual(20, video_tools.get_start_frame_from_segment(result_noise1[0]))
        self.assertEqual(80, video_tools.get_end_frame_from_segment(result_noise1[0]))
        result_noise2, errors = video_tools.formMaskDiff(fileOne,
                                                         modFiles[2],
                                                         modFiles[2],
                                                         'AddNoise',
                                                         startSegment=None,
                                                         endSegment=None,
                                                         analysis=analysis,
                                                         alternateFunction=video_tools.detectCompare,
                                                         arguments={})
        self.assertTrue(len(result_noise2) >= 1)
        self.assertEqual(
            video_tools.get_end_frame_from_segment(result_noise2[0]) - video_tools.get_start_frame_from_segment(
                result_noise2[0]) + 1, video_tools.get_frames_from_segment(result_noise2[0]))
        self.assertEqual(20, video_tools.get_start_frame_from_segment(result_noise1[0]))
        self.assertEqual(80, video_tools.get_end_frame_from_segment(result_noise1[0]))

    def testMaskSet(self):
        source = self.locateFile('tests/videos/sample1.mov')
        source_set1 = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator(source),
                                                           start_time='29', end_time='55')
        source_set2 = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator(source),
                                                           start_time='29', end_time='55')
        self.assertEquals(source_set1, source_set2)

    def test_lossy(self):
        self.assertFalse(video_tools.is_raw_or_lossy_compressed(self.locateFile('tests/videos/sample1.mov')))
        video_tools.x264(self.locateFile('tests/videos/sample1.mov'), 'sample1_ffr_3.mp4')
        self.files_to_remove.append('sample1_ffr_3.mp4')
        self.assertTrue(video_tools.is_raw_or_lossy_compressed('sample1_ffr_3.mp3'))

    def testMetaDiff(self):
        from maskgen.support import getValue
        meta_diff = video_tools.form_meta_data_diff(self.locateFile('tests/videos/sample1.mov'),
                                                                self.locateFile('tests/videos/sample1_slow_swap.mov'),
                                                                media_types=['video'])
        self.assertTrue('nb_frames' in getValue({'metadatadiff': meta_diff}, 'metadatadiff.video', {}))
        self.assertTrue(meta_diff['video']['duration_ts'] == ('change', '35610', '610304'))
        meta_diff = video_tools.form_meta_data_diff(self.locateFile('tests/videos/sample1.mov'),
                                                                self.locateFile('tests/videos/sample1_slow_swap.mov'),
                                                                media_types=['video', 'audio'])
        self.assertTrue(meta_diff['stereo']['bit_rate'] == ('change', '126228', '128273'))
        self.assertTrue(meta_diff['video']['bit_rate'] == ('change', '2298880', '1364992'))

        meta_diff = video_tools.form_meta_data_diff(self.locateFile('tests/videos/sample1.mov'),
                                                                self.locateFile('tests/videos/sample1_slow_swap.mov'),
                                                                media_types=['audio'])
        self.assertTrue(meta_diff['stereo']['nb_frames'] == ('change', '2563', '2558'))


    def test_buf_to_int(self):
        stream =  np.random.randint(-1000,1000,128,dtype=np.int16)
        self.assertTrue(np.all(stream == video_tools.buf_to_int(stream.tostring(),2)))

    def test_audio_reader(self):
        video_tools.audioWrite('test_tat.0.0.wav', 8192*1024)
        self.filesToKill.append('test_tat.0.0.wav')
        c1 = video_tools.AudioReader('test_tat.0.0.wav','all',block=8192)
        block = c1.getBlock(10000,128)
        c1.close()
        c1 = video_tools.AudioReader('test_tat.0.0.wav','all', block=8192)
        position = c1.findBlock(block, 0)
        self.assertIsNotNone(position)
        self.assertEqual(10000,position[0])
        c1.close()
        block = block[1::2]
        c1 = video_tools.AudioReader('test_tat.0.0.wav', 'right', block=8192)
        position = c1.findBlock(block, 0)
        self.assertIsNotNone(position)
        self.assertEqual(10000, position[0])
        c1.close()

        video_tools.audioWrite('test_tat1.0.0.wav', 8192 * 10,channels=1)
        self.filesToKill.append('test_tat1.0.0.wav')
        c1 = video_tools.AudioReader('test_tat1.0.0.wav', 'all', block=8192)
        block = c1.getBlock(10000, 128)
        c1.close()
        c1 = video_tools.AudioReader('test_tat1.0.0.wav', 'all', block=8192)
        position = c1.findBlock(block, 0)
        self.assertIsNotNone(position)
        self.assertEqual(10000, position[0])
        c1.close()


        import wave
        wf = wave.open('test_tat2.0.0.wav', 'wb')
        wf.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
        value = np.random.randint(-32767, 32767, 1024*1024, dtype=np.int16)
        packed_value = value.tobytes()
        wf.writeframesraw(packed_value)
        wf.close()
        self.filesToKill.append('test_tat2.0.0.wav')
        wf = wave.open('test_tat3.0.0.wav', 'wb')
        wf.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
        value1 = np.random.randint(-32767, 32767, 2*1024 * 1024, dtype=np.int16)
        value1[0:40000:2] = value[0:20000]
        value1[46000::2] = value[23000:]
        packed_value = value1.tobytes()
        wf.writeframesraw(packed_value)
        wf.close()
        self.filesToKill.append('test_tat3.0.0.wav')
        c1 = video_tools.AudioReader('test_tat2.0.0.wav', 'all', block=8192)
        c2 = video_tools.AudioReader('test_tat3.0.0.wav', 'left', block=8192)
        self.assertIsNone(c1.compareToOtherReader(c2, min_threshold=0))
        c1.nextBlock()
        c2.nextBlock()
        c1.nextBlock()
        c2.nextBlock()
        self.assertEquals((20000,23000-1), c1.compareToOtherReader(c2, min_threshold=0))
        c1.close()
        c2.close()

        wf = wave.open('test_tat4.0.0.wav', 'wb')
        wf.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
        value2 = np.random.randint(-32767, 32767, 2 * 1024 * 1024, dtype=np.int16)
        value2[0:40000] = value1[0:40000]
        value2[46000:] = value1[46000:]
        packed_value = value2.tobytes()
        wf.writeframesraw(packed_value)
        wf.close()
        c1 = video_tools.AudioReader('test_tat3.0.0.wav', 'all', block=8192)
        c2 = video_tools.AudioReader('test_tat4.0.0.wav', 'all', block=8192)
        self.assertIsNone(c1.compareToOtherReader(c2, min_threshold=0))
        c1.nextBlock()
        c2.nextBlock()
        c1.nextBlock()
        c2.nextBlock()
        self.assertEquals((20000, 23000 - 1), c1.compareToOtherReader(c2, min_threshold=0))
        c1.close()
        c2.close()

        c1 = video_tools.AudioReader('test_tat3.0.0.wav', 'right', block=8192)
        c2 = video_tools.AudioReader('test_tat4.0.0.wav', 'right', block=8192)
        self.assertIsNone(c1.compareToOtherReader(c2, min_threshold=0))
        c1.nextBlock()
        c2.nextBlock()
        c1.nextBlock()
        c2.nextBlock()
        self.assertEquals((20000, 23000 - 1), c1.compareToOtherReader(c2, min_threshold=0))
        c1.close()
        c2.close()

        wf = wave.open('test_tat5.0.0.wav', 'wb')
        wf.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
        value3 = np.random.randint(-32767, 32767, 2 * 1024 * 1024, dtype=np.int16)
        value3[0:40000:2] = value2[1:40000:2]
        value3[46000::2] = value2[46001::2]
        packed_value = value3.tobytes()
        wf.writeframesraw(packed_value)
        wf.close()
        c1 = video_tools.AudioReader('test_tat4.0.0.wav', 'right', block=8192)
        c2 = video_tools.AudioReader('test_tat5.0.0.wav', 'left', block=8192)
        self.assertIsNone(c1.compareToOtherReader(c2, min_threshold=0))
        c1.nextBlock()
        c2.nextBlock()
        c1.nextBlock()
        c2.nextBlock()
        self.assertEquals((20000, 23000 - 1), c1.compareToOtherReader(c2, min_threshold=0))
        c1.close()
        c2.close()



    def test_intersection(self):
        amount = 30
        sets = []
        change = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=1000,
            endframe=amount,
            frames=amount,
            rate=30,
            error=1.1,
            type='video')
        sets.append(change)
        change = video_tools.create_segment(
            starttime=2500,
            startframe=75,
            endtime=3500,
            endframe=75 + amount - 1,
            frames=amount,
            rate=30,
            error=1.2,
            type='video')
        sets.append(change)

        result = video_tools.dropFramesFromMask([video_tools.create_segment(**{
            'startframe': 90,
            'starttime': 3000,
            'endframe': 100,
            'endtime': 4000
        })], sets)
        self._add_mask_files_to_kill(result)
        self.assertEqual(3, len(result))
        self.assertEqual(15, video_tools.get_frames_from_segment(result[1]))
        self.assertEqual(75, video_tools.get_start_frame_from_segment(result[1]))
        self.assertEqual(89, video_tools.get_end_frame_from_segment(result[1]))
        self.assertEqual(90, video_tools.get_start_frame_from_segment(result[2]))
        self.assertEqual(93, video_tools.get_end_frame_from_segment(result[2]))
        self.assertEqual(1.1, video_tools.get_error_from_segment(result[0]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[2]))
        self.assertEqual(1.2, video_tools.get_error_from_segment(result[1]))

    def testAudio(self):
        from maskgen.tool_set import VidTimeManager
        video_tools.audioWrite('test_ta.0.0.wav', 512)
        self.filesToKill.append('test_ta2.0.0.wav')
        self.filesToKill.append('test_ta.0.0.wav')
        self.filesToKill.append('test_ta3.0.0.wav')
        self.filesToKill.append('test_ta4.0.0.wav')
        self.filesToKill.append('test_ta5.0.0.wav')
        self.filesToKill.append('test_ta6.0.0.wav')
        augmentAudio('test_ta.0.0.wav', 'test_ta2.0.0.wav', addNoise)
        augmentAudio('test_ta.0.0.wav', 'test_ta3.0.0.wav', sampleFrames)
        singleChannelSample('test_ta.0.0.wav', 'test_ta4.0.0.wav')
        singleChannelSample('test_ta.0.0.wav', 'test_ta5.0.0.wav', skip=1)
        insertAudio('test_ta.0.0.wav', 'test_ta6.0.0.wav', pos=28, length=6)
        deleteAudio('test_ta.0.0.wav', 'test_ta7.0.0.wav', pos=28, length=6)

        result, errors = video_tools.audioDeleteCompare('test_ta.0.0.wav', 'test_ta7.0.0.wav', 'test_ta_del', VidTimeManager())
        self.assertEqual(1, len(result))
        self.assertEqual(113, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(136, video_tools.get_end_frame_from_segment(result[0]))

        result, errors = video_tools.audioInsert('test_ta.0.0.wav', 'test_ta6.0.0.wav', 'test_ta_c', VidTimeManager())
        self.assertEqual(1, len(result))
        self.assertEqual(29, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(40, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(video_tools.get_end_frame_from_segment(result[0]),
                         video_tools.get_start_frame_from_segment(result[0]) + video_tools.get_frames_from_segment(
                             result[0]) - 1)

        result, errors = video_tools.audioCompare('test_ta.0.0.wav', 'test_ta2.0.0.wav', 'test_ta_c', VidTimeManager())
        self.assertEqual(1, len(result))
        self.assertEqual(7, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(255, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(video_tools.get_end_frame_from_segment(result[0]),
                         video_tools.get_start_frame_from_segment(result[0]) + video_tools.get_frames_from_segment(
                             result[0]) - 1)

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta3.0.0.wav', 'test_ta_s1', VidTimeManager(startTimeandFrame=(0,7)))
        self.assertEqual(1, len(result))
        self.assertEqual(7, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(48, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(video_tools.get_end_frame_from_segment(result[0]),
                         video_tools.get_start_frame_from_segment(result[0]) + video_tools.get_frames_from_segment(
                             result[0]) - 1)

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta3.0.0.wav', 'test_ta_s1',
                                                 VidTimeManager(startTimeandFrame=(0, 0)))
        self.assertEqual(1, len(result))
        self.assertEqual(7, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(48, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(video_tools.get_end_frame_from_segment(result[0]),
                         video_tools.get_start_frame_from_segment(result[0]) + video_tools.get_frames_from_segment(
                             result[0]) - 1)


        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta4.0.0.wav', 'test_ta_s2', VidTimeManager(startTimeandFrame=(0,3)))
        self.assertEqual(1, len(result))
        self.assertEqual(4, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(24, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(video_tools.get_end_frame_from_segment(result[0]),
                         video_tools.get_start_frame_from_segment(result[0]) + video_tools.get_frames_from_segment(
                             result[0]) - 1)

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta4.0.0.wav', 'test_ta_s2',
                                                 VidTimeManager(startTimeandFrame=(0, 0)))
        self.assertEqual(1, len(result))
        self.assertEqual(4, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(24, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(video_tools.get_end_frame_from_segment(result[0]),
                         video_tools.get_start_frame_from_segment(result[0]) + video_tools.get_frames_from_segment(
                             result[0]) - 1)

        result, errors = video_tools.audioSample('test_ta.0.0.wav', 'test_ta5.0.0.wav', 'test_ta_s3', VidTimeManager(),
                                                 arguments={'Copy Stream': 'right'})
        self.assertEqual(1, len(result))
        self.assertEqual(4, video_tools.get_start_frame_from_segment(result[0]))
        self.assertEqual(24, video_tools.get_end_frame_from_segment(result[0]))
        self.assertEqual(video_tools.get_end_frame_from_segment(result[0]),
                         video_tools.get_start_frame_from_segment(result[0]) + video_tools.get_frames_from_segment(
                             result[0]) - 1)

    def tearDown(self):
        for f in set(self.filesToKill):
            if os.path.exists(f):
                os.remove(f)


if __name__ == '__main__':
    unittest.main()
