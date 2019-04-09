import unittest
from tests.test_support import TestSupport
from maskgen.cv2api import cv2api_delegate
import numpy as np
from subprocess import Popen, PIPE
from maskgen import ffmpeg_api
import os
from maskgen.video_tools import pasteCompare
from maskgen.tool_set import VidTimeManager,convertToVideo
from maskgen.image_wrap import ImageWrapper
from collections import OrderedDict

from skimage.draw import random_shapes

def make_image():
    i = np.random.randint(0,255,(200,256,4),dtype='uint8')
    i[:,:,3] = 0
    shape = random_shapes((200, 256), max_shapes=4,allow_overlap=True,
                  intensity_range=((100, 255)),num_channels=1)
    shape = shape[0].reshape((200,256))
    i[:,:,3][shape[:]<255] =255
    return i


codecs = OrderedDict([('raw',['-vcodec', 'rawvideo']),
                      ('mp4v', ['-c:v', 'mpeg4', '-crf','0'])])

suffices = {'raw':'avi',
            'mp4v':'m4v'}

fourccs = {
    'raw':0,
    'mp4v':cv2api_delegate.get_fourcc('mp4v')}


def make_video(input_filename, codec):
    ffmpegcommand = ffmpeg_api.get_ffmpeg_tool()
    command = [ffmpegcommand, '-y', '-i', input_filename]
    command.extend(codecs[codec])
    video_prefix = input_filename[:input_filename.rfind('.') + 1]
    outFileName = video_prefix + suffices[codec]
    outFileName = os.path.split(outFileName)[1]
    command.append(outFileName)
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    try:
        return outFileName if p.returncode == 0 else None
    except OSError as e:
        print (e)
    return video_prefix


def save_result(result, codec):
    import json
    killList = []
    for seg in result:
        seg.pop('mask')
        maskvid_filename = convertToVideo(seg['videosegment'])
        killList.append(maskvid_filename)
    json_filename = codec + '.json'
    with open(json_filename, 'w') as fp:
        json.dump(result, fp)
    killList.append(json_filename)
    return killList


class TestMaskGeneration(TestSupport):
    filesToKill = []

    def setUp(self):
        self.mv = self.locateFile('tests/videos/sample1.mov')
        self.test_image = make_image()
        ImageWrapper(self.test_image).save('test_paste.png')

    def paste_in(self,frame,object):
        diff_x = frame.shape[0] - object.shape[0]
        x = int(diff_x/2.0 - (np.random.randint(-20,20,(1))[0]))
        diff_y = frame.shape[1] - object.shape[1]
        y = int(diff_y / 2.0 - np.random.randint(-20,20,(1))[0])
        part = frame[x:x+object.shape[0],y:y+object.shape[1],:]
        part[object[:,:,3]>0] = object[:,:,0:3][object[:,:,3]>0]
        frame[x:x + object.shape[0], y:y + object.shape[1]] = part
        return frame

    def paste(self, video_file, object, codec):
        vfi = cv2api_delegate.videoCapture(video_file)
        width = int(vfi.get(cv2api_delegate.prop_frame_width))
        height = int(vfi.get(cv2api_delegate.prop_frame_height))
        fourcc = fourccs[codec]
        video_prefix = video_file[:video_file.rfind('.')]
        video_file_output = video_prefix + '_paste.' + suffices[codec]
        video_file_output = os.path.split(video_file_output)[1]
        vfo = cv2api_delegate.videoWriter(video_file_output, fourcc, (vfi.get(cv2api_delegate.prop_fps)), (width, height))
        if not vfo.isOpened():
            raise ValueError('VideoWriter failed to open.')
        try:
            while vfi.isOpened() and vfo.isOpened():
                r,f = vfi.read()
                if not r:
                    break
                i = ImageWrapper(self.paste_in(f,object),mode='BGR')
                vfo.write(i.image_array)
        finally:
            vfi.release()
            vfo.release()
            self.addFileToRemove(video_file_output)
        return video_file_output

    def run_test(self, codec):
        pre_of = make_video(self.mv, codec)
        self.addFileToRemove(pre_of)
        post_of = self.paste(pre_of, self.test_image, codec)
        self.addFileToRemove(post_of)
        result, errors = pasteCompare(pre_of, post_of, post_of, VidTimeManager(), arguments={'add type': 'replace'})
        _filesToKill = save_result(result, codec)
        for _file in _filesToKill:
            self.addFileToRemove(_file)

    def test_raw(self):
        self.run_test('raw')

    def test_mpeg4(self):
        self.run_test('mp4v')


if __name__ == '__main__':
    unittest.main()
