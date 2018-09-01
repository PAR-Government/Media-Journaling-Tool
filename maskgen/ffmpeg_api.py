#FFUN WITH FFMPEG

import os, StringIO, tempfile
import uuid, time
from subprocess import Popen, PIPE
import logging
import itertools
from support import getValue



def get_ffmpeg_tool():
    return os.getenv('MASKGEN_FFMPEGTOOL', 'ffmpeg');

def get_ffprobe_tool():
    return os.getenv('MASKGEN_FFPROBETOOL', 'ffprobe');

def ffmpeg_tool_check():
    ffmpegcommand = [get_ffprobe_tool(), '-L']
    try:
        p = Popen(ffmpegcommand, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
    except:
        return ffmpegcommand[0]+ ' not installed properly'

    ffmpegcommand = [get_ffmpeg_tool(), '-L']
    try:
        p = Popen(ffmpegcommand, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
    except:
        return ffmpegcommand[0] + ' not installed properly'
    return None

def run_ffmpeg(args, noOutput=True, tool=get_ffmpeg_tool()):
    command = [tool] if tool is not None else []
    command.extend(args)
    try:
        pcommand = Popen(command, stdout=PIPE if not noOutput else None, stderr=PIPE)
        stdout, stderr = pcommand.communicate()
        if pcommand.returncode != 0:
            print stderr
            error = ' '.join([line for line in str(stderr).splitlines() if line.startswith('[')])
            raise ValueError(error)
        if noOutput == False:
            return stdout
    except OSError as e:
        logging.getLogger('maskgen').error("FFmpeg not installed")
        logging.getLogger('maskgen').error(str(e))
        raise e

def _run_command(command,outputCollector=None):
    try:
        stdout = run_ffmpeg(command, noOutput=False, tool=None)
        if outputCollector is not None:
            for line in stdout.splitlines():
                outputCollector.append(line)
    except ValueError as e:
        return [e.message]
    return []

def __get_channel_data(source_data, codec_type):
    for data in source_data:
        if getValue(data,'codec_type','na') == codec_type:
            return data

def get_ffmpeg_version():
    try:
        stdout = run_ffmpeg(['-version'], noOutput=False)
        return  stdout.split()[2][0:3]
    except:
        pass
    return "?"

def __add_meta_to_frames(frames, meta, index_id='stream_index'):
    if len(meta) > 0 and index_id in meta:
        index = int(meta[index_id])
        while index >= len(frames):
            frames.append([])
        frames[index].append( meta )
        meta.pop(index_id)
        return index

def __add_meta_to_list(frames, meta, index_id='index'):
    if len(meta) > 0 and index_id in meta:
        index = int(meta[index_id])
        while index >= len(frames):
            frames.append({})
        frames[index] = meta
        meta.pop(index_id)
        return index

def sort_frames(frames):
    for k, v in frames.iteritems():
        frames[k] = sorted(v, key=lambda meta: meta['pkt_pts_time'])

def process_frames_from_stream(stream, errorstream):
    frames = []
    meta = {}
    while True:
        line = stream.readline()
        if line is None or len(line) == 0:
            break
        if '[/FRAME]' in line:
            __add_meta_to_frames(frames, meta)
            meta = {}
        else:
            parts = line.split('=')
            if len(parts) > 1:
                meta[parts[0].strip()] = parts[1].strip()
    __add_meta_to_frames(frames, meta)
    return frames

def process_meta_from_streams(stream, errorstream):
    streams = []
    meta = {}
    bit_rate = None
    video_stream = None
    try:
        while True:
            line = errorstream.readline()
            if line is None or len(line) == 0:
                break
            pos = line.find('bitrate:')
            if pos > 0:
                bit_rate = line[pos+9:].strip()
                pos = bit_rate.find(' ')
                if pos > 0:
                    bit_rate = str(int(bit_rate[0:pos]) * 1024)
                    break
    except:
        pass
    while True:
        line = stream.readline()
        if line is None or len(line) == 0:
            break
        if '[STREAM]' in line or '[FORMAT]' in line:
            while True:
                line = stream.readline()
                if '[/STREAM]' in line:
                    index = __add_meta_to_list(streams, meta, index_id ='index')
                    if getValue(meta,'codec_type','na') == 'video' and video_stream is None:
                        video_stream = index
                    meta = {}
                    break
                elif '=' not in line:
                    continue
                else:
                    setting = line.split('=')
                    if len(setting) < 2 or len(setting[1]) == 0:
                        continue
                    meta[setting[0]] = '='.join(setting[1:]).strip()
    if len(meta) > 0:
        index = __add_meta_to_list(streams, meta, index_id='index')
        if getValue(meta, 'codec_type', 'na') == 'video' and video_stream is None:
            video_stream = index
    if bit_rate is not None and video_stream is not None and \
            ('bit_rate' is not streams[video_stream]  or \
                     streams[video_stream]['bit_rate'] == 'N/A'):
        streams[video_stream]['bit_rate'] = bit_rate
    return streams


def add_to_meta_data(meta, prefix, line, split=True):
    parts = line.split(',') if split else [line]
    for part in parts:
        pair = [x.strip().lower() for x in part.split(': ')]
        if len(pair) > 1 and pair[1] != '':
            if prefix != '':
                meta[prefix + '.' + pair[0]] = pair[1]
            else:
                meta[pair[0]] = pair[1]


def get_stream_id_from_line(line):
    start = line.find('#')
    if start > 0:
        end = line.find('(', start)
        end = min(end, line.find(': ', start))
        return line[start:end]
    return ''

def get_stream_indices_of_type(stream_data, stream_type):
    """
    Get indexes of the streams that are of a given type
    :param stream_data: metadata with stream information.
    :param stream_type: codec_type to look for.
    :return: list of indexes in string form.
    @rtype: list of str
    """
    indicies = []
    for pos in range(len(stream_data)):
        if getValue(stream_data[pos],'codec_type','na') == stream_type:
            indicies.append(pos)
    return indicies if len(indicies) > 0 else None

def process_stream_meta(stream, errorstream):
    meta = {}
    prefix = ''
    while True:
        line = stream.readline()
        if line is None or len(line) == 0:
            break
        if 'Stream' in line:
            prefix = get_stream_id_from_line(line)
            splitPos = line.find(': ')
            meta[line[0:splitPos].strip()] = line[splitPos + 2:].strip()
            continue
        if 'Duration' in line:
            add_to_meta_data(meta, prefix, line)
        else:
            add_to_meta_data(meta, prefix, line, split=False)
    return meta

def get_meta_from_video(file, with_frames=False, show_streams=False, media_types=['video', 'audio'], extras=None):

    def strip(meta,frames,media_types):
        return [item for item in meta if getValue(item,'codec_type','na') in media_types],\
               [frames[pos] for pos in range(len(frames)) if getValue(meta[pos],'codec_type','na') in media_types] \
                   if len(frames) > 0 else frames

    def runProbeWithFrames(func, args=None):
        if len(media_types) == 1:
            ffmpegcommand = [get_ffprobe_tool(), '-select_streams', media_types[0][0]]
        else:
            ffmpegcommand = [get_ffprobe_tool()]
       # if extras is not None:
       #     ffmpegcommand.append('-show_entries')
       #     ffmpegcommand.append('-packet:' + ','.join(extras))
        ffmpegcommand.append(file)
        if args != None:
            ffmpegcommand.append(args)
        stdout_fd, stdout_path = tempfile.mkstemp('.txt',
                                                  'stdout_{}_{}'.format(uuid.uuid4(),
                                                                        str(os.getpid())))
        try:
            stder_fd, stder_path = tempfile.mkstemp('.txt',
                                                    'stderr_{}_{}'.format(uuid.uuid4(),
                                                                          str(os.getpid())))
            try:
                p = Popen(ffmpegcommand, stdout=stdout_fd, stderr=stder_fd)
                p.wait()
            finally:
                os.close(stder_fd)
        finally:
            os.close(stdout_fd)

        try:
            with open(stdout_path) as stdout_fd:
                with open(stder_path) as stder_fd:
                    return func(stdout_fd,stder_fd)
        finally:
            persistantDelete(stder_path)
            persistantDelete(stdout_path)

    def persistantDelete(path, attempts=10):
        if os.path.exists(path):
            for x in range(attempts):
                try:
                    os.remove(path)
                    break
                except WindowsError:
                    time.sleep(0.1)
        if os.path.exists(path):
            logging.getLogger('maskgen').warn("Failed to remove file {}".format(path))

    def runProbe(func, args=None):
        ffmpegcommand = [get_ffprobe_tool(), file]
        if args != None:
            ffmpegcommand.extend(args.split())
        stdout, stder = Popen(ffmpegcommand, stdout=PIPE, stderr=PIPE).communicate()
        return func(StringIO.StringIO(stdout), StringIO.StringIO(stder))

    if show_streams or with_frames:
        args = '-show_streams' + (' -select_streams {}'.format(media_types[0][0]) if len(media_types) == 1 else '')
        meta = runProbe(process_meta_from_streams, args=args)
    else:
        meta = runProbe(process_stream_meta, args='')

    if with_frames:
        frames = runProbeWithFrames(process_frames_from_stream, args='-show_frames')
    else:
        # insure match of frames to meta
        frames = []

    return strip(meta, frames, media_types)

def get_frame_attribute(fileOne, attribute, default=None, audio=False):
    ffmpegcommand = get_ffprobe_tool()
    results = []
    errors = _run_command([ffmpegcommand,
                          '-show_entries', 'stream={},codec_type'.format(attribute),
                          fileOne],
                         outputCollector=results)
    if len(results) > 0:
        streams = []
        for result in results:
            if result.find('[STREAM]') >= 0:
                streams.append(dict())
                continue
            parts = result.split('=')
            if len(parts) < 2:
                continue
            streams[-1][parts[0]] = parts[1]
        for stream in streams:
            if (audio and getValue(stream,'codec_type','na') == 'audio') or \
                    (not audio and getValue(stream,'codec_type','na') != 'audio'):
                return stream[attribute]

    return default

def get_video_frame_rate_from_meta(meta, frames):
    index = get_stream_indices_of_type(meta, 'video')[0]
    r = getValue(meta[index],'r_frame_rate','30/1')
    avg = getValue(meta[index],'avg_frame_rate',r)
    parts = avg.split('/')
    if parts[0] == 'N':
        parts = r.split('/')
    if parts[0] != 'N':
        return float(parts[0]) / int(parts[1]) if len(parts) > 0 and int(parts[1]) != 0 else float(parts[0])
    return len(frames[index])/float(getValue(meta[index],'duration',1)) if len(index) < len(frames) else \
        float(getValue(meta[index], 'nb_frames', 30))/float(getValue(meta[index],'duration',1))

def is_vfr(meta):
    """

    :param meta:
    :return: based on meta data for video, is the stream variable frame rate
    @rtype: bool
    """
    nb = getValue(meta,'nb_frames','N/A')
    avg = getValue(meta,'avg_frame_rate','N/A')
    r = getValue(meta,'r_frame_rate','N/A')
    if (r[0] != 'N' and r != avg) or r[0] in ['N','0']  or nb[0] in ['N','0']:
        return True
    # approach requires frames which is more expensive to gather but more efficient
    #first_frame_duration = 0
    #idx = 0
    #for frame in frames:
    #    if idx > 0:
    ##        frame_duration = round(float(frame['pkt_pts_time']) - float(frames[idx-1]['pkt_pts_time']), 10)
    #        if first_frame_duration == 0:
    #            first_frame_duration = frame_duration
    #        if frame_duration != first_frame_duration:
    #            return True
    #    idx += 1
    return False
