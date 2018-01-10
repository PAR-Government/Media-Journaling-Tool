import maskgen.video_tools
import logging


def get_channel_data(source_data, codec_type):
    pos = 0
    for data in source_data:
        if data['codec_type'] == codec_type:
            return data,pos
        pos+=1


def orient_rotation_positive(rotate):
    rotate = -rotate
    if rotate < 0:
        rotate = 360 + rotate
    return rotate


def get_item(data, item, default_value):
    if item not in data:
        return default_value
    return data[item]


def get_rotation_filter(difference):
    if abs(difference) == 180:
        return 'transpose=2,transpose=2'
    elif difference == -90:
        return 'transpose=2'
    elif difference == 90:
        return 'transpose=1'
    else:
        return None


def save_as_video(source, target, donor, matchcolor=False, apply_rotate = True):
    import maskgen.exif
    import maskgen.video_tools
    """
    Saves image file using quantization tables
    :param source: string filename of source image
    :param target: string filename of target (result). target should have same extension as donor.
    :param donor: string filename of donor MP4
    """
    ffmpeg_version = maskgen.video_tools.get_ffmpeg_version()
    skipRotate = ffmpeg_version[0:3] == '3.3' or not apply_rotate
    source_data = maskgen.video_tools.getMeta(source, show_streams=True)[0]
    donor_data = maskgen.video_tools.getMeta(donor, show_streams=True)[0]
    video_settings = {'-codec:v': 'codec_name', '-b:v': 'bit_rate', '-r': 'r_frame_rate', '-pix_fmt': 'pix_fmt',
                      '-profile:v': 'profile'}
    profile_map = [('Baseline', 'baseline'),
                   ('Main', 'main'),
                   ('4:4:4', 'high444'),
                   ('4:2:2', 'high422'),
                   ('High 10', 'high10'),
                   ('High', 'high')
                   ]
    if matchcolor:
        video_settings.update(
            {'-color_primaries': 'color_primaries', '-color_trc': 'color_transfer', '-colorspace': 'color_space'})
    audio_settings = {'-codec:a': 'codec_name', '-b:a': 'bit_rate', '-channel_layout': 'channel_layout'}
    ffargs = ['-i', source]
    rotated = 'no'
    diff_rotation = 0
    for streamid in range(len(donor_data)):
        data = donor_data[streamid]
        if data['codec_type'] == 'video':
            if data['nb_frames'] in ['unknown','N/A']:
                ffargs.extend(['-vsync', '2'])
                data['r_frame_rate'] = 'N/A'
            for option, setting in video_settings.iteritems():
                if setting == 'profile' and setting in data:
                    for tup in profile_map:
                        if data[setting].find(tup[0]) >= 0:
                            ffargs.extend([option, tup[1]])
                            break
                elif setting in data and data[setting] not in  ['unknown','N/A']:
                    ffargs.extend([option, data[setting]])

            try:
                width = data['width']
                height = data['height']
                source_channel_data, source_streamid = get_channel_data(source_data, 'video')
                source_width = source_channel_data['width']
                source_height = source_channel_data['height']
                # source_aspect = source_channel_data['display_aspect_ratio']
                donor_rotation = int(get_item(data, 'rotation', 0))
                diff_rotation = donor_rotation - int(get_item(source_channel_data, 'rotation', 0))
                if diff_rotation != 0:
                    rotation_filter = get_rotation_filter(diff_rotation)
                    rotation = str(orient_rotation_positive(donor_rotation)) if donor_rotation != 0 else None
                else:
                    rotation_filter = get_rotation_filter(donor_rotation)
                    rotation = str(orient_rotation_positive(donor_rotation)) if donor_rotation != 0 else None
                filters = ''
                # do we only include these settings IF there is a difference?
                if skipRotate:
                    rotated = 'no'
                    if rotation_filter is not None:
                        logging.getLogger('maskgen').warn(
                            'The donated video has rotation meta-data. The target video will not match the characteristcs of the donor.')
                    if abs(diff_rotation) == 90:
                        old_width = width
                        width= height
                        height = old_width
                    if source_height != width or source_width != height:
                        video_size = width + ':' + height
                        try:
                            if 'display_aspect_ratio' in data:
                                aspect_ratio = ',setdar=' + data['display_aspect_ratio']
                            else:
                                aspect_ratio = ''
                        except KeyError:
                            aspect_ratio = ''
                        filters += ('scale=' + video_size + aspect_ratio)
                    if len(filters) > 0:
                        ffargs.extend(['-vf'])
                        ffargs.append(filters)
                else:
                    if (abs(diff_rotation) == 90 and (source_height != width or source_width != height)) or \
                            (abs(diff_rotation) != 90 and (source_height != height or source_width != width)):
                        video_size = width + ':' + height
                        try:
                            if 'display_aspect_ratio' in data:
                                aspect_ratio = ',setdar=' + data['display_aspect_ratio']
                            else:
                                aspect_ratio = ''
                        except KeyError:
                            aspect_ratio = ''
                        filters += ('scale=' + video_size + aspect_ratio)
                    if rotation_filter is not None:
                        filters += (',' + rotation_filter if len(filters) > 0 else rotation_filter)
                        rotated = 'yes'
                        if ffmpeg_version[0:3] == '3.3':
                            logging.getLogger('maskgen').error(
                                'FFMPEG version {} does no support setting rotation meta-data. {}'.format(
                                ffmpeg_version,
                                'The target video will not match the characteristcs of the donor. '))
                    if len(filters) > 0:
                        ffargs.extend(['-vf'])
                        ffargs.append(filters)
                    if rotation is not None:
                        ffargs.extend(['-metadata:s:v:' + str(source_streamid), 'rotate=' + rotation])
            except KeyError:
                continue
            if 'TAG:language' in data:
                ffargs.extend(['-metadata:s:v:' + str(source_streamid), 'language=' + data['TAG:language']])
        elif data['codec_type'] == 'audio':
            for option, setting in audio_settings.iteritems():
                if setting in data and data[setting] != 'unknown':
                    ffargs.extend([option, data[setting]])

    ffargs.extend(['-map_metadata', '0:g','-y', target])

    logging.getLogger('masken').info(str(ffargs))
    maskgen.video_tools.runffmpeg(ffargs)

    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target], ignoreError=True)
    maskgen.exif.runexif(['-P', '-q', '-m', '-tagsFromFile', donor,  target], ignoreError=True)
    maskgen.exif.runexif(['-overwrite_original','-P', '-q', '-m', '-XMPToolkit=', target], ignoreError=True)
    createtime = maskgen.exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target],
                             ignoreError=True)
    return {'rotate': rotated, 'rotation':diff_rotation}

def transform(img, source, target, **kwargs):
    donor = kwargs['donor']
    container = kwargs['container'] if 'container' in kwargs else 'match'
    rotate = 'rotate' not in kwargs or kwargs['rotate'] == 'yes'
    matchcolor = 'match color characteristics' in kwargs and kwargs['match color characteristics'] == 'yes'
    analysis = {}
    if container != 'match':
        targetname = target[0:target.rfind('.')+1] + container
        analysis = {'override_target': targetname}
    else:
        targetname  = target
    analysis.update(save_as_video(source, targetname, donor, matchcolor=matchcolor,apply_rotate=rotate))
    return analysis,None



def operation():
    return {'name': 'AntiForensicCopyExif',
            'category': 'AntiForensic',
            'description': 'Convert video to donor filetype and copy metadata.',
            'software': 'ffmpeg',
            'version': maskgen.video_tools.get_ffmpeg_version(),
            'arguments': {
                'donor': {
                    'type': 'donor',
                    'defaultvalue': None,
                    'description': 'Video with desired metadata'
                },
                'match color characteristics': {
                    'type': 'yesno',
                    'defaultvalue': 'no'
                },
                'container': {
                    'type': 'list',
                    'values':['match','mov','avi','mp4'],
                    'defaultvalue': 'match'
                }
            },
            'transitions': [
                'video.video'
            ]
            }


def suffix():
    return 'donor'
