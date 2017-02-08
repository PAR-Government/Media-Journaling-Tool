import maskgen.exif
import maskgen.video_tools

def save_as_video(source, target, donor):
    """
    Saves image file using quantization tables
    :param source: string filename of source image
    :param target: string filename of target (result). target should have same extension as donor.
    :param donor: string filename of donor MP4
    """
    donor_data = maskgen.video_tools.getMeta(donor, show_streams=True)
    video_settings = {'-codec:v':'codec_name', '-b:v':'bit_rate', '-r':'r_frame_rate', '-pix_fmt':'pix_fmt', '-profile:v':'profile'}
    audio_settings = {'-codec:a':'codec_name', '-b:a':'bit_rate', '-channel_layout':'channel_layout'}
    ffargs = ['-i', source]
    for data in donor_data:
            if data['codec_type'] == 'video':
                for option, setting in video_settings.iteritems():
                    if setting in data:
                        ffargs.extend([option, data[setting]])
                try:
                    width = data['width']
                    height = data['height']
                    video_size = width + ':' + height
                    try:
                        aspect_ratio = ',setdar=' + data['display_aspect_ratio']
                    except KeyError:
                        aspect_ratio = ''
                    ffargs.extend(['-vf', 'scale=' + video_size + aspect_ratio])
                except KeyError:
                    continue
            elif data['codec_type'] == 'audio':
                for option, setting in audio_settings.iteritems():
                    if setting in data:
                        ffargs.extend([option, data[setting]])
    ffargs.extend(['-y', target])

    maskgen.video_tools.runffmpeg(ffargs)

    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor, '-all:all', '-unsafe', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-XMPToolkit=', target])
    createtime = maskgen.exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        maskgen.exif.runexif(['-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target])

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    save_as_video(source, target, donor)
    
    return None,None
    
def operation():
    return {'name':'AntiForensicCopyExif',
            'category':'AntiForensic',
            'description':'Convert video to donor filetype and copy metadata.',
            'software':'ffmpeg',
            'version':'2.8.4',
            'arguments':{
                'donor':{
                    'type':'donor',
                    'defaultvalue':None,
                    'description':'Video with desired metadata'
                }
            },
            'transitions':[
                'video.video'
            ]
            }

def suffix():
    return 'donor'
