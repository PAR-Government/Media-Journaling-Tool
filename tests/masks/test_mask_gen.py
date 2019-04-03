import unittest
from maskgen.cv2api import cv2api_delegate
import numpy as np
from subprocess import Popen, PIPE
import math, random
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
                      ('mp4v', ['-c:v', 'mpeg4', '-crf','0']),
                      ('x264', ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf','0']),
                      ('x265', ['-c:v', 'libx265','-preset','medium','-x265-params', '--lossless', '-crf','0'])])

suffices = {'raw':'avi','x264':'avi','x265':'avi','mp4v':'m4v'}

fourccs = {'raw':0,
'mp4v':cv2api_delegate.get_fourcc('MP4V'),
           'x264':cv2api_delegate.get_fourcc('H264'),
           'x265': cv2api_delegate.get_fourcc('HEVC')}


def make_video(input_filename, codec):
    ffmpegcommand = ffmpeg_api.get_ffmpeg_tool()

    command = [ffmpegcommand, '-y', '-i', input_filename]
    command.extend(codecs[codec])
    video_prefix = input_filename[:input_filename.rfind('.') + 1]
    outFileName = video_prefix + suffices[codec]
    command.append(outFileName)
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    try:
        return outFileName if p.returncode == 0 else None
    except OSError as e:
       print e
    return video_prefix

def save_result(dir,result,codec):
    import json
    for seg in result:
        seg.pop('mask')
        convertToVideo(os.path.join(dir,seg['videosegment']))
    with open(os.path.join(dir,codec + '.json'),'w') as fp:
       json.dump(result,fp)

class MyTestCase(unittest.TestCase):


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
        fourcc = fourccs[codec ]
        video_prefix = video_file[:video_file.rfind('.')]
        video_file_output = video_prefix + '_paste.' + suffices[codec]
        vfo = cv2api_delegate.videoWriter(video_file_output,fourcc,(vfi.get(cv2api_delegate.prop_fps)), (width, height))
        try:
            while vfi.isOpened():
                r,f = vfi.read()
                if not r:
                    break
                i = ImageWrapper(self.paste_in(f,object),mode='BGR')
                vfo.write(i.image_array)
                #i= i.convert('RGB')
                #i.save(os.path.join(os.path.dirname(video_file),'t.png'))

        finally:
            vfi.release()
            vfo.release()
        return video_file_output

    def test_something(self):
        dir = '/Users/ericrobertson/Downloads/tp'
        mv = 'IMG_2976.MOV'
        ifile = os.path.join(dir,mv)
        test_image = make_image()
        ImageWrapper(test_image).save(os.path.join(dir, 'test_paste.png'))
        for codec in codecs:
            print 'next: {}'.format(codec)
            pre_of = make_video(ifile,codec)
            post_of = self.paste(pre_of,test_image,codec)
            result,errors = pasteCompare(pre_of,post_of,post_of,VidTimeManager(),arguments={'add type':'replace'})
            save_result(dir,result,codec)


if __name__ == '__main__':
    unittest.main()
