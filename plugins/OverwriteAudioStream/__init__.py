import maskgen.video_tools
import maskgen.tool_set
"""
Concatentate or Replace donor audio to video.
"""
def transform(img,source,target, **kwargs):
    whichones = kwargs['Stream'] if 'Stream' in kwargs else 'both'
    donor = kwargs['donor']
    donor_data = maskgen.video_tools.getMeta(donor, show_streams=True)[0]
    milli, frame = maskgen.tool_set.getMilliSecondsAndFrameCount(kwargs['Start Time'])
    channelspecifier = ':1' if whichones == 'right' else (':0' if whichones=='left' else '')
    streamno = 0
    if len(donor_data) > 0:
        streamno = [x for x in (idx for idx, val in enumerate(donor_data) if val['codec_type'] == 'audio')][0]
    command = ['-y','-i',source,'-i',donor]
    if milli is not None and milli > 0:
        command.extend(['-filter_complex',
                        '[0:a]atrim=start=0:end=' + \
                        maskgen.tool_set.getSecondDurationStringFromMilliseconds(milli) + \
                        '[aout];[1:a]atrim=start=0[bout];[aout][bout]concat=n=2:v=0:a=1[allout]',
                        '-map',
                        '0:v',
                        '-map',
                        '[allout]',
                        '-c:v',
                        'copy',
                        target])
    elif frame > 0:
        command.extend(['-filter_complex',
                        '[0:a]atrim=start_sample=0:end_sample={}'.format(frame) + \
                        '[aout];[1:a]atrim=start=0[bout];[aout][bout]concat=n=2:v=0:a=1[allout]',
                        '-map',
                        '0:v',
                        '-map',
                        '[allout]',
                        '-c:v',
                        'copy',
                        target])
    else:
        command.extend(['-map','0:v','-map','1:'+str(streamno)+channelspecifier,'-c','copy',target])


    maskgen.video_tools.runffmpeg(command,noOutput=True)
    return {'add type': 'replace','synchronization':'none'},None
    
def operation():
    return {'name':'AddAudioSample',
            'category':'Audio',
            'description':'Add Audio Stream to Video.  The Start time is insertion point over the original video',
            'software':'FFMPEG',
            'version':'3.2',
            'arguments': {
                'donor': {
                    'type': 'donor'
                },
                'add type' : {
                    'type': 'str',
                    'defaultvalue': 'replace'
                },
                'synchronization': {
                    'type': 'str',
                    'defaultvalue': 'none'
                },
                'Start Time': {
                    'type': 'int',
                    'defaultvalue': 0
                }
            },
            'transitions': [
                'video.video',
                'audio.video'
            ]
        }

def suffix():
    return None
