#FFUN WITH FFMPEG

import os, StringIO, tempfile
import uuid, time
from subprocess import Popen, PIPE
import logging
import itertools
from support import getValue


def getFFmpegTool():
    return os.getenv('MASKGEN_FFMPEGTOOL', 'ffmpeg');


def getFFprobeTool():
    return os.getenv('MASKGEN_FFPROBETOOL', 'ffprobe');


def runffmpeg(args, noOutput=True):
    command = [getFFmpegTool()]
    command.extend(args)
    try:
        pcommand = Popen(command, stdout=PIPE if not noOutput else None, stderr=PIPE)
        stdout, stderr = pcommand.communicate()
        if pcommand.returncode != 0:
            error = ' '.join([line for line in str(stderr).splitlines() if line.startswith('[')])
            raise ValueError(error)
        if noOutput == False:
            return stdout
    except OSError as e:
        logging.getLogger('maskgen').error("FFmpeg not installed")
        logging.getLogger('maskgen').error(str(e))
        raise e


def get_ffmpeg_version():
    command = [getFFmpegTool(),'-version']
    try:
        pcommand = Popen(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = pcommand.communicate()
        if pcommand.returncode != 0:
            logging.getLogger('maskgen').error(str(stderr) if stderr is not None else '')
        else:
            return stdout.split()[2][0:3]
    except OSError as e:
        logging.getLogger('maskgen').error("FFmpeg not installed")
        logging.getLogger('maskgen').error(str(e))
    return '?'

def __addMetaToFrames(frames, meta):
    if len(meta) > 0 and 'stream_index' in meta:
        index = meta['stream_index']
        if index not in frames:
            frames[index] = []
        frames[index].append(meta)
        meta.pop('stream_index')

def processFrames(stream, errorstream):
    frames = {}
    meta = {}
    while True:
        line = stream.readline()
        if line is None or len(line) == 0:
            break
        if '[/FRAME]' in line:
            __addMetaToFrames(frames, meta)
            meta = {}
        else:
            parts = line.split('=')
            if len(parts) > 1:
                meta[parts[0].strip()] = parts[1].strip()
    __addMetaToFrames(frames, meta)
    return frames

def processMetaStreams(stream,errorstream):
    streams = []
    temp = {}
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
                if '[/STREAM]' in line or '[/FORMAT]' in line:
                    streams.append(temp)
                    temp = {}
                    break
                else:
                    setting = line.split('=')
                    temp[setting[0]] = '='.join(setting[1:]).strip()
                    if setting[0] == 'codec_type' and temp[setting[0]] == 'video':
                        video_stream = len(streams)
    if bit_rate is not None and video_stream is not None and \
            ('bit_rate' is not streams[video_stream]  or \
                     streams[video_stream]['bit_rate'] == 'N/A'):
        streams[video_stream]['bit_rate'] = bit_rate
    return streams


def addToMeta(meta, prefix, line, split=True):
    parts = line.split(',') if split else [line]
    for part in parts:
        pair = [x.strip().lower() for x in part.split(': ')]
        if len(pair) > 1 and pair[1] != '':
            if prefix != '':
                meta[prefix + '.' + pair[0]] = pair[1]
            else:
                meta[pair[0]] = pair[1]


def getStreamId(line):
    start = line.find('#')
    if start > 0:
        end = line.find('(', start)
        end = min(end, line.find(': ', start))
        return line[start:end]
    return ''

def getStreamindexesOfType(stream_data, stream_type):
    """
    Get indexes of the streams that are of a given type
    :param stream_data: metadata with stream information.
    :param stream_type: codec_type to look for.
    :return: list of indexes in string form.
    @rtype: list of str
    """
    indicies = []
    for data in stream_data:
        if data['codec_type'] == stream_type:
            indicies.append(data['index'])
    return indicies if len(indicies) > 0 else None

def processMeta(stream,errorstream):
    meta = {}
    prefix = ''
    while True:
        line = stream.readline()
        if line is None or len(line) == 0:
            break
        if 'Stream' in line:
            prefix = getStreamId(line)
            splitPos = line.find(': ')
            meta[line[0:splitPos].strip()] = line[splitPos + 2:].strip()
            continue
        if 'Duration' in line:
            addToMeta(meta, prefix, line)
        else:
            addToMeta(meta, prefix, line, split=False)
    return meta


def getMeta(file, with_frames=False, show_streams=False,media_types=['video','audio'],extras=None):

    def runProbeWithFrames(func, args=None):
        if len(media_types) == 1:
            ffmpegcommand = [getFFprobeTool(),'-select_streams',media_types[0][0]]
        else:
            ffmpegcommand = [getFFprobeTool()]
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
        ffmpegcommand = [getFFprobeTool(), file]
        if args != None:
            ffmpegcommand.append(args)
        stdout, stder = Popen(ffmpegcommand, stdout=PIPE, stderr=PIPE).communicate()
        return func(StringIO.StringIO(stdout), StringIO.StringIO(stder))

    if with_frames:
        frames = runProbeWithFrames(processFrames,args='-show_frames')
    else:
        frames = {}
    if show_streams:
        meta = runProbe(processMetaStreams, args='-show_streams')
    else:
        meta = runProbe(processMeta, args='-show_streams')

    return meta, frames

def getVideoFrameRate(meta, frames):
    index = getStreamindexesOfType(meta, 'video')[0]
    r = getValue(meta[int(index)],'r_frame_rate','30/1')
    avg = getValue(meta[int(index)],'avg_frame_rate',r)
    parts = avg.split('/')
    if parts[0] == 'N':
        parts = r.split('/')
    if parts[0] != 'N':
        return float(parts[0]) / int(parts[1]) if len(parts) > 0 and int(parts[1]) != 0 else float(parts[0])
    return len(frames[index])/float(getValue(meta[int(index)],'duration',1)) if index in frames else 30

def isVFRVideo(meta):
    """

    :param meta:
    :return: based on meta data for video, is the stream variable frame rate
    @rtype: bool
    """
    avg = getValue(meta,'avg_frame_rate','N/A')
    r = getValue(meta,'r_frame_rate','N/A')
    if (r[0] != 'N' and r != avg) or r[0] == 'N':
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
