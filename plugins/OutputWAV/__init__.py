import maskgen.video_tools

"""
Save Audio channels to a WAV file
"""


def transform(img, source, target, **kwargs):
    maskgen.video_tools.toAudio(source, outputName=target)
    return None, None


def operation():
    return {'name': 'OutputAudioPCM',
            'category': 'Output',
            'description': 'Extract Audio Stream from Video',
            'software': 'ffmpeg',
            'version': maskgen.video_tools.get_ffmpeg_version(),
            'arguments': {
            },
            'transitions': [
                'video.audio'
            ]
            }


def suffix():
    return '.wav'
