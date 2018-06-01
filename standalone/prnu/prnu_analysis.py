"""
@author Mike Hurlbutt
"""

import sys
import subprocess
import os

import numpy as np
import cv2
from maskgen.cv2api import cv2api_delegate
from maskgen.plugins import findPlugin

"""
Acquire every frame depending on the number of desired frames
and the gap between selections and the capture
"""
def getFrameList(videoCapture, gap, frames):
    f = None
    count = 0.0
    while count < frames:
        for x in range(0, gap):
            t = videoCapture.grab()  # only decode necessary frames
            if not t:
                break
        more_frames, frame = videoCapture.retrieve()
        if not more_frames:
            break
        if count == 0:
            f = np.array(frame).astype('float64')
        else:
            f += np.array(frame).astype('float64')
        count += 1
    return (f / (count))


"""
Calculates average image from 3600 evenly distributed frames of a video
or if less than 3600 then all frames are used
"""
def averageFrame(donor):
    frames = 100.0
    cap = cv2api_delegate.videoCapture(donor)
    try:
        total = cap.get(cv2api_delegate.prop_frame_count)
        if total == 0:
            raise ValueError("Video Could not be Accessed")
        if frames > total:
            frames = total
        gap = int(total / frames)
        f = getFrameList(cap, gap, frames)
        ext = os.path.splitext(donor)[1]
        trace = donor.replace(ext, '_avg.png')
        #cv2.imwrite(trace,np.roll(f, 1, -1))
        cv2.imwrite(trace, f)
        return trace
    finally:
        cap.release()

def main():
    source = sys.argv[1]
    sourceImg = averageFrame(source)

    if sys.platform.startswith('win'):
        subprocess.call([os.path.join(findPlugin('PRNURemoveFromVid'), 'ExtractNoise.exe'), sourceImg])
    else:
        subprocess.call([os.path.join(findPlugin('PRNURemoveFromVid'), 'ExtractImageNoise'), sourceImg])

if __name__ == "__main__":
    sys.exit(main())
