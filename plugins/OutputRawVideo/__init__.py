from maskgen.video_tools import outputRaw
import maskgen
"""
Save te image as AVI using Raw Video.
"""
def transform(img,source,target, **kwargs):
    outputRaw(source,target)
    return None,None
    
def operation():
    return {'name':'OutputAVI',
            'category':'Output',
            'description':'Save an video as .avi using codec rawvideo',
            'software':'ffmpeg',
            'version':maskgen.video_tools.get_ffmpeg_version(),
            'arguments':{
            },
            'transitions': [
                'video.video'
            ]
        }

def suffix():
    return '.avi'
