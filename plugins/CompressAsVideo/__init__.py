# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from os import path
import maskgen.video_tools
import maskgen.ffmpeg_api
import shlex # For handling paths with spaces
import logging
from collections import OrderedDict


def validate_codec_name(codec_name, codec_type='video'):
    """
    Checks if a name is in the list of valid codecs.
    :param codec_name: string, name to be checked.
    :param codec_type: string, type of codec to check for.
    """
    codec_valid = codec_name in maskgen.video_tools.get_valid_codecs(codec_type)
    if not codec_valid:
        errmsg = 'The Operation was NOT successful \n\n' \
                 + 'Invalid Codec- ' + codec_type + ' codec ' + codec_name + ' is not available to encode with.'
        raise ValueError(errmsg.strip())


def validate_codecs(args):
    """
    Attempts to validate the codec names found in the args list.
    :param args: list of ffmpeg arguments
    """
    video_name = get_codec_name(args, 'video')
    if video_name:
        try:
            validate_codec_name(video_name, 'video')
        except ValueError as e:
            e.message += '\n\n' + 'FFmpeg command string: \n' + build_command_string(args) + '\n May be copied from the console or logfile'
            raise ValueError(e.message)

    audio_name = get_codec_name(args, 'audio')
    if audio_name:
        try:
            validate_codec_name(audio_name, 'audio')
        except ValueError as e:
            e.message += '\n\n' + 'FFmpeg command string: \n' + build_command_string(args) + '\n May be copied from the console or logfile'
            raise ValueError(e.message)


def get_codec_name(args, codec_type='video'):
    """
    Search list of arguments for the codec name.
    :param args: list of ffmpeg arguments
    :param codec_type: string, type of codec to check for.
    :returns: string, name of codec.
    """
    try:
        query = '-codec:v' if codec_type == 'video' else '-codec:a'
        codec_index = args.index(query) + 1
    except ValueError:
        return ''
    return args[codec_index]

def replace_codec_name(args, oldName, newName):
    """
    Replace name of codec with another
    :param args: list of ffmpeg arguments
    :param oldName: string, name to be replaced
    :param newName: string, name to replace with
    """
    index = args.index(oldName)
    args[index] = newName


def compare_codec_tags(donor_path, output_path):
    """
    Check the output video codec tags for similarity to the donor video, raises error if fail
    :param donor_path: Path to the donor video file
    :param output_path: Path to the output video file
    """
    donor_data = maskgen.ffmpeg_api.get_meta_from_video(donor_path, show_streams=True)[0]
    output_data = maskgen.ffmpeg_api.get_meta_from_video(output_path, show_streams=True)[0]

    donor_video_data = get_channel_data(donor_data, 'video')
    donor_audio_data = get_channel_data(donor_data, 'audio')
    output_video_data = get_channel_data(output_data, 'video')
    output_audio_data = get_channel_data(output_data, 'audio')

    donor_video_tag = donor_audio_tag = output_video_tag = output_audio_tag = ''

    if donor_video_data != None:
        donor_video_tag = (donor_video_data[0]['codec_tag_string'] + '/'
                        + donor_video_data[0]['codec_tag'])
    if donor_audio_data != None:
        donor_audio_tag = (donor_audio_data[0]['codec_tag_string'] + '/'
                        + donor_audio_data[0]['codec_tag'])
    if output_video_data != None:
        output_video_tag = (output_video_data[0]['codec_tag_string'] + '/'
                        + output_video_data[0]['codec_tag'])
    if output_audio_data != None:
        output_audio_tag = (output_audio_data[0]['codec_tag_string'] + '/'
                        + output_audio_data[0]['codec_tag'])

    if output_video_tag != donor_video_tag or output_audio_tag != donor_audio_tag:
        errmsg = 'The operation was successful!\n\n'
        if output_video_tag != donor_video_tag:
            errmsg += "Video Codec Tags do not match: \n" + "Donor: " + donor_video_tag + "\nOutput: " + output_video_tag + '\n\n'
        if output_audio_tag != donor_audio_tag:
            errmsg += "Audio Codec Tags do not match: \n" + "Donor: " + donor_audio_tag + "\nOutput: " + output_audio_tag + '\n\n'
        errmsg += 'FYI- This manipulation may be vulnerable to detection by comparing the metadata.'
        raise ValueError(errmsg)

def get_channel_data(source_data, codec_type):
    pos = 0
    for data in source_data:
        if data['codec_type'] == codec_type:
            return data, pos
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

def parse_override_command(command, source, target):
    """
    Build the FFmpeg command arguments from the override string
    :param command: string, the override instructions from the plugin window
    :return: list of strings, ready for passing to runffmpeg.
    """
    command = command.lower()
    args = shlex.split(command, r"'")
    y_index = args.index('-y') if '-y' in args else None
    if y_index == None:
        args.append('-y')
    if not path.exists(args[-1]):
        args.append(target)
    try:
        inp = args.index('-i')
    except ValueError:
        args.insert(0,'-i')
        args.insert(1,source)
    for term in args:
        if term == ' ' or term == 'ffmpeg':
            args.remove(term)
    return args

def build_command_string(args=[]):
    """
    Convert the list of arguments to a single string for export to the user pastebin
    :param args: list of strings, ffmpeg arguments
    :return: string, ready for pasting.
    """
    cmd = 'ffmpeg'
    for term in args:
        test = str(term) #to get rid of unicode
        if path.isdir(path.split(test)[0]):
            term = r"'" + test + r"'"
        cmd += ' ' + term.strip()
    return cmd.strip()

def save_as_video(source, target, donor, matchcolor=False, apply_rotate=True, video_codec='use donor', audio_codec='use donor', allow_override=False, override_cmd=''):
    import maskgen.video_tools
    """
    Saves image file using quantization tables
    :param source: string filename of source image
    :param target: string filename of target (result). target should have same extension as donor.
    :param donor: string filename of donor MP4
    """
    ffmpeg_version = maskgen.video_tools.get_ffmpeg_version()
    skipRotate = ffmpeg_version[0:3] == '3.3' or not apply_rotate
    source_data = maskgen.ffmpeg_api.get_meta_from_video(source, show_streams=True)[0]
    donor_data = maskgen.ffmpeg_api.get_meta_from_video(donor, show_streams=True)[0]

    video_settings = {'-codec:v': 'codec_name', '-b:v': 'bit_rate', '-r': 'r_frame_rate', '-pix_fmt': 'pix_fmt',
                      '-profile:v': 'profile'}
    # not a dictionary for case sensistivity
    profile_map = [('Baseline', 'baseline'),
                   ('Main', 'main'),
                   ('4:4:4', 'high444'),
                   ('4:2:2', 'high422'),
                   ('High 10', 'high10'),
                   ('High', 'high')
                   ]

    # limited supported from progress to interlaced top or bottom first.
    # does not appear to support top coded first, bottom displayed first and vice versa
    # progressive conversion if a filter conversion and not a flag.
    # supposedly, some version of ffmpeg support the an deinterlace option, but not all.
    field_order_map= {'tt':['-flags', '+ilme+ildct', '-top', '1'],
                      'bb':['-flags', '+ilme+ildct', '-top', '0'],
                      'tb':['-flags', '+ilme+ildct', '-top', '1'],
                      'bt':['-flags', '+ilme+ildct', '-top', '0']}
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
            filters = ''
            rotation = None
            source_channel_data, source_streamid = get_channel_data(source_data, 'video')
            if 'field_order' in data and \
                ('field_order' not in source_channel_data or source_channel_data['field_order'] != data['field_order']):
                if data['field_order'] in field_order_map:
                    ffargs.extend(field_order_map[data['field_order']])
                elif data['field_order'] == 'progressive':
                    # let auto parity detection.  Could have looked at the field order and mapping top first to 0
                    # bottom first to 1, thus yadif=1:parity:1
                    filters += ',yadif=1'
                else:
                    logging.getLogger('maskgen').warn('Unable to update the field order; too many options')
            if data['nb_frames'] in ['unknown','N/A']:
                ffargs.extend(['-vsync', '2'])
                data['r_frame_rate'] = 'N/A'
            for option, setting in video_settings.iteritems():
                if setting == 'profile':
                    if setting in data and video_codec.lower() == 'use donor':
                        for tup in profile_map:
                            if data[setting].find(tup[0]) >= 0:
                                ffargs.extend([option, tup[1]])
                                ffargs.extend(['-level', data['level']])
                                break
                    continue
                elif setting in data and data[setting] not in ['unknown', 'N/A']:
                    ffargs.extend([option, data[setting]])

            try:
                width = data['width']
                height = data['height']
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
                        dar = get_item(data, 'display_aspect_ratio', 'N/A')
                        if dar != 'N/A':
                            aspect_ratio = ',setdar=' + dar.replace(':', '/')
                        else:
                            aspect_ratio = ',setdar=' + str(float(width)/float(height))
                        filters += (',scale=' + video_size + aspect_ratio)
                else:
                    if (abs(diff_rotation) == 90 and (source_height != width or source_width != height)) or \
                            (abs(diff_rotation) != 90 and (source_height != height or source_width != width)):
                        video_size = width + ':' + height
                        dar = get_item(data, 'display_aspect_ratio', 'N/A')
                        if dar != 'N/A':
                            aspect_ratio = ',setdar=' + dar.replace(':', '/')
                        else:
                            aspect_ratio = ',setdar=' + str(float(width) / float(height))
                        filters += (',scale=' + video_size + aspect_ratio)
                    if rotation_filter is not None and  len(rotation_filter) > 0:
                        filters += (',' + rotation_filter)
                        rotated = 'yes'
                        if ffmpeg_version[0:3] == '3.3':
                            logging.getLogger('maskgen').error(
                                'FFMPEG version {} does no support setting rotation meta-data. {}'.format(
                                ffmpeg_version,
                                'The target video will not match the characteristcs of the donor. '))
            except KeyError:
                continue
            if len(filters) > 0:
                ffargs.extend(['-vf'])
                ffargs.append(filters[1:])
            if rotation is not None:
                ffargs.extend(['-metadata:s:v:' + str(source_streamid), 'rotate=' + rotation])
            if 'TAG:language' in data:
                ffargs.extend(['-metadata:s:v:' + str(source_streamid), 'language=' + data['TAG:language']])
        elif data['codec_type'] == 'audio':
            for option, setting in audio_settings.iteritems():
                if setting in data and data[setting] != 'unknown':
                    ffargs.extend([option, data[setting]])

    ffargs.extend(['-map_metadata', '0:g', '-y', target])

    # Codec overrides
    if video_codec.lower() != 'use donor':
        replace_codec_name(ffargs, get_codec_name(ffargs, 'video'), video_codec)
    if audio_codec.lower() != 'use donor':
        replace_codec_name(ffargs, get_codec_name(ffargs, 'audio'), audio_codec)

    # Total override
    if allow_override and override_cmd != '':
        ffargs = parse_override_command(override_cmd, source, target)

    #logging.getLogger('maskgen').info("Running ffmpeg with:" + str(ffargs))

    # Check Codec names before running
    validate_codecs(ffargs)

    maskgen.ffmpeg_api.run_ffmpeg(ffargs, False)

    maskgen.exif.runexif(['-overwrite_original', '-all=', target], ignoreError=True)
    maskgen.exif.runexif(['-P', '-m', '-tagsFromFile', donor,  target], ignoreError=True)
    maskgen.exif.runexif(['-overwrite_original','-P', '-m', '-XMPToolkit=', target], ignoreError=True)
    createtime = maskgen.exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        maskgen.exif.runexif(['-overwrite_original', '-P', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target],
                             ignoreError=True)

    # Check the codec tags after.
    try:
        compare_codec_tags(donor, target)
    except ValueError:
        logging.getLogger('maskgen').warn("Codec mismatch between output and donor. FFmepg command: \n" + build_command_string(ffargs))

    return {'rotate': rotated, 'rotation':diff_rotation}

def transform(img, source, target, **kwargs):
    donor = kwargs['donor']
    container = kwargs['container'] if 'container' in kwargs else 'match'
    rotate = 'rotate' not in kwargs or kwargs['rotate'] == 'yes'
    matchcolor = 'match color characteristics' in kwargs and kwargs['match color characteristics'] == 'yes'
    audio_codec_preference = kwargs['Audio Codec'] if 'Audio Codec' in kwargs else 'use donor'
    video_codec_preference = kwargs['Video Codec'] if 'Video Codec' in kwargs else 'use donor'
    allow_override = 'Allow Override' in kwargs and kwargs['Allow Override'] == 'yes'
    override_command = str(kwargs['Command Override']).strip() if 'Command Override' in kwargs else str('')
    analysis = {}
    if container != 'match':
        targetname = target[0:target.rfind('.')+1] + container
        analysis = {'override_target': targetname}
    else:
        targetname = target[0:target.rfind('.')] + path.splitext(donor)[1]
        analysis = {'override_target': targetname}

    analysis.update(save_as_video(source, targetname, donor, matchcolor=matchcolor, apply_rotate=rotate,
                                  video_codec=video_codec_preference, audio_codec=audio_codec_preference,
                                  allow_override=allow_override, override_cmd=override_command))
    return analysis, None


def operation():
    return {'name': 'AntiForensicCopyExif',
            'category': 'AntiForensic',
            'description': 'Convert video to donor filetype and copy metadata.',
            'software': 'ffmpeg',
            'version': maskgen.video_tools.get_ffmpeg_version(),
            'arguments': OrderedDict([
                ('donor', {
                    'type': 'donor',
                    'defaultvalue': None,
                    'description': 'Video with desired metadata'
                }),
                ('match color characteristics', {
                    'type': 'yesno',
                    'defaultvalue': 'no'
                }),
                ('container', {
                    'type': 'list',
                    'values': ['match', 'mov', 'avi', 'mp4'],
                    'defaultvalue': 'match'
                }),
                ('Video Codec', {
                    'type': 'list',
                    'values': maskgen.video_tools.get_valid_codecs(codec_type='video'),
                    'defaultvalue': 'Use Donor'
                }),
                ('Audio Codec', {
                    'type': 'list',
                    'values': maskgen.video_tools.get_valid_codecs(codec_type='audio'),
                    'defaultvalue': 'Use Donor'
                }),
                ('Command Override', {
                    'type': 'text',
                    'values': '',
                }),
                ('Allow Override', {
                    'type': 'yesno',
                    'defaultvalue': 'no'
                    }
                 )]),
            'transitions': [
                'video.video'
            ]
            }


def suffix():
    return 'donor'
