from maskgen.video_tools import x264
from maskgen import exif
import maskgen
"""
Save te image as MP4 using X264 loss encoding.
"""
def transform(img,source,target, **kwargs):

    crf = int(kwargs['crf']) if 'crf' in kwargs else 0
    x264(source,outputname=target,crf=crf)
    orientation_source = exif.getOrientationFromExif(source)
    orientation_target = exif.getOrientationFromExif(target)
    analysis = {"Image Rotated": "no"}
    if orientation_source is not None and orientation_source != orientation_target:
        analysis = {"Image Rotated": "yes"}
    return analysis,None
    
def operation():
    return {'name':'OutputAVI',
            'category':'Output',
            'description':'Save an video as .mp4 using codec X264',
            'software':'ffmpeg',
            'version':maskgen.video_tools.get_ffmpeg_version(),
            'arguments':{
                'crf':{
                    'type':'int[0:100]',
                    'defaultvalue':'0',
                    'description':'Constraint Rate Factor. 0 is lossless'
                }
            },
            'transitions': [
                'video.video'
            ]
        }

def suffix():
    return '.avi'
