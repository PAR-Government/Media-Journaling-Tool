import maskgen.exif
import maskgen.video_tools

def get_channel_data(source_data, codec_type):
    for data in source_data:
        if data['codec_type'] == codec_type:
            return data

def orient_rotation_positive(rotate):
    rotate = -rotate
    if rotate < 0:
        rotate = 360+rotate
    return rotate

def get_item(data,item,default_value):
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

def save_as_video(source, target, donor, matchcolor=False):
    """
    Saves image file using quantization tables
    :param source: string filename of source image
    :param target: string filename of target (result). target should have same extension as donor.
    :param donor: string filename of donor MP4
    """
    source_data = maskgen.video_tools.getMeta(source, show_streams=True)[0]
    donor_data = maskgen.video_tools.getMeta(donor, show_streams=True)[0]
    video_settings = {'-codec:v':'codec_name', '-b:v':'bit_rate', '-r':'r_frame_rate', '-pix_fmt':'pix_fmt',
                      '-profile:v':'profile'}
    profile_map  = [('Baseline','baseline'),
                    ('Main','main'),
                    ('4:4:4','high444'),
                    ('4:2:2','high422'),
                    ('High 10','high10'),
                    ('High','high')
                    ]
    if matchcolor:
        video_settings.update(
            {'-color_primaries':'color_primaries', '-color_trc':'color_transfer', '-colorspace':'color_space'})
    audio_settings = {'-codec:a':'codec_name', '-b:a':'bit_rate', '-channel_layout':'channel_layout'}
    ffargs = ['-i', source]
    rotated = 'no'
    for streamid in range(len(donor_data)):
            data = donor_data[streamid]
            if data['codec_type'] == 'video':
                for option, setting in video_settings.iteritems():
                    if setting == 'profile' and setting in data:
                        for tup in profile_map:
                            if data[setting].find(tup[0]) >= 0:
                                ffargs.extend([option, tup[1]])
                                break
                    elif setting in data and data[setting] != 'unknown':
                        ffargs.extend([option, data[setting]])

                try:
                    width = data['width']
                    height = data['height']
                    source_channel_data = get_channel_data(source_data, 'video')
                    source_width = source_channel_data['width']
                    source_height = source_channel_data['height']
                    source_aspect = source_channel_data['display_aspect_ratio']
                    donor_rotation = int(get_item(data, 'rotation', 0))
                    diff_rotation = donor_rotation - int(get_item(source_channel_data, 'rotation', 0))
                    if diff_rotation != 0:
                        rotation_filter = get_rotation_filter(diff_rotation)
                        rotation = str(orient_rotation_positive(donor_rotation)) if donor_rotation != 0 else None
                    else:
                        rotation_filter = None #get_rotation_filter(donor_rotation)
                        rotation = None# str(orient_rotation_positive(donor_rotation)) if donor_rotation != 0 else None
                    filters = ''
                    # do we only include these settings IF there is a difference?
                    if (abs(diff_rotation) == 90 and (source_height != width or source_width != height)) or \
                       (abs(diff_rotation) != 90 and (source_height != height or source_width != width)):
                        video_size = width + ':' + height
                        try:
                            aspect_ratio = ',setdar=' + data['display_aspect_ratio']
                        except KeyError:
                            aspect_ratio = ''
                        filters+=('scale=' + video_size + aspect_ratio)
                    if rotation_filter is not None:
                        filters+=  (',' + rotation_filter if len(filters) > 0 else rotation_filter)
                        rotated = 'yes'
                    if len(filters) > 0:
                        ffargs.extend(['-vf'])
                        ffargs.append(filters)
                    if rotation is not None:
                       ffargs.extend(['-metadata:s:v:' + str(streamid), 'rotate=' + rotation])
                except KeyError:
                    continue
            elif data['codec_type'] == 'audio':
                for option, setting in audio_settings.iteritems():
                    if setting in data and data[setting] != 'unknown':
                        ffargs.extend([option, data[setting]])
            if 'TAG:language' in data:
                ffargs.extend(['-metadata:s:v:' + str(streamid), 'language=' + data['TAG:language']])
    ffargs.extend(['-y', target])

    maskgen.video_tools.runffmpeg(ffargs)

    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target],ignoreError=True)
    maskgen.exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor, '-all:all', '-unsafe', target],ignoreError=True)
    maskgen.exif.runexif(['-P', '-q', '-m', '-XMPToolkit=', target],ignoreError=True)
    createtime = maskgen.exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        maskgen.exif.runexif(['-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target],ignoreError=True)
    return {'rotated':rotated}

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    matchcolor = 'match color characteristics' in kwargs and kwargs['match color characteristics'] == 'yes'
    return  save_as_video(source, target, donor, matchcolor =matchcolor),None
    
def operation():
    return {'name':'AntiForensicCopyExif',
            'category':'AntiForensic',
            'description':'Convert video to donor filetype and copy metadata.',
            'software':'ffmpeg',
            'version':'3.2.2',
            'arguments':{
                'donor':{
                    'type':'donor',
                    'defaultvalue':None,
                    'description':'Video with desired metadata'
                },
                'match color characteristics': {
                    'type': 'yesno',
                    'defaultvalue': 'no'
                }
            },
            'transitions':[
                'video.video'
            ]
            }

def suffix():
    return 'donor'
