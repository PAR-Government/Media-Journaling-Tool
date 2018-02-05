
from maskgen import video_tools

def transform(img,source,target, **kwargs):
    from maskgen import video_tools
    channel = kwargs['Copy Stream'] if 'Copy Stream' in kwargs else None
    starttime = kwargs['Start Time'] if 'Start Time' in kwargs else None
    endtime = kwargs['End Time'] if 'End Time' in kwargs else None
    video_tools.toAudio(source,target,channel=channel, start=starttime, end=endtime)
    return None,None

def suffix():
    return ".wav"

def operation():
    return {'name':'AudioSample',
            'category':'Audio',
            'description':'Extract Audio from video',
            'software':'ffmpeg',
            'version':video_tools.get_ffmpeg_version(),
            'arguments':{
                },
            'transitions':[
                'video.audio'
                ]
            }
