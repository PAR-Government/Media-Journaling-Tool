from os import path
from collections import namedtuple
from pydub.utils import db_to_float
from pydub import effects, silence
from pydub import *
import pydub.exceptions
import itertools
import numpy as np

def preprocess_audio(source_path, format='wav'):
    """Prepares audio for processing"""
    try:
        if format != 'avi':
            sound_original = AudioSegment.from_file(source_path, format)
        else:
            sound_original = AudioSegment.from_file(source_path)
    except pydub.exceptions.CouldntDecodeError:
        raise ValueError("FFmpeg couldn't decode the input media- try Output WAV/AVI first.")
    if sound_original.channels == 2:
        channels = sound_original.split_to_mono()
        sound_original = channels[0].overlay(channels[1]) #merge to mono
    sound_preProcessed = effects.normalize(sound_original)  # Adjust gain in case source is really quiet/loud
    return sound_preProcessed

def range_to_segment(source_seg, range):
    """Helper- generates an audio segment given a range"""
    return source_seg[range[0]:range[1]]

def range_between_ranges(range_from, range_to):
    """Helper- returns the range between two ranges."""
    return range_from[1], range_to[0]

def extent_of_ranges(range_from, range_to):
    """Helper- returns the length of the outer extents of two ranges in ms"""
    return range_to[1] - range_from[0]

def length_of_range(range):
    """Helper- returns the length of a range from start to finish in ms"""
    return range[1] - range[0]

def export_audio(sound, output_path):
    """Helper- exports audioSegment to output_path"""
    sound.export(output_path, format=path.splitext(output_path)[1][-3:])

def compare_audio_segments(sound1, sound2):
    """convert to numpy arrays and get the difference."""
    samples1 = np.array(sound1.get_array_of_samples())
    samples2 = np.array(sound2.get_array_of_samples())
    diff = np.mean(np.sqrt((samples1 - samples2) ** 2))
    return diff

def cut_n_stitch(sound, range_to_cut, crossfade_length):
    before = sound[:range_to_cut[0]]
    after = sound[range_to_cut[1]:]
    return before.append(after, crossfade=crossfade_length)


class SilenceProcessor():

    src_path = ''
    a_format = '' #format of the input media
    min_drop = 2.0 #sec
    max_drop = 4.0 #sec
    fade_length = 100 #ms
    original = None
    processed = None

    Match = namedtuple('Match', ['silenceA', 'silenceB', 'score'])

    def __init__(self, source_path, min_drop_length=2, max_drop_length=4, crossfade_length=100):
        self.src_path = source_path
        self.a_format = path.splitext(source_path)[1].replace('.', '')
        self.min_drop = float(min_drop_length) #s
        self.max_drop = float(max_drop_length) #s
        self.fade_length = int(crossfade_length) #ms
        if self.a_format == 'avi':
            self.original = AudioSegment.from_file(self.src_path)# format=self.a_format)
        else:
            self.original = AudioSegment.from_file(self.src_path, format=self.a_format)
        self.processed = preprocess_audio(self.src_path, self.a_format)

    def valid_silences(self, silences):
        first_nonsilent = self.get_first_nonsilent(self.processed)
        for a in silences:
            valid =[s for s in silences if s[0] > a[1] and s[0] > first_nonsilent[0]]
            for b in valid:
                if (extent_of_ranges(a,b) >= self.min_drop*1000 and extent_of_ranges(a, b) <= self.max_drop*1000):
                    yield a, b

    def scan_silence(self, sound, silence_range_a, silence_range_b):
        """Compare all parts of one silence to all parts of another silence,
        score for similarity, return list of all matches"""
        matches = []
        silence_from = range_to_segment(sound, silence_range_a)
        silence_to = range_to_segment(sound, silence_range_b)
        #Divide each silence into steps of 10, to reduce number of comparisons
        step_from = int(len(silence_from)/10)
        step_to = int(len(silence_from)/10)
        for a in range(0, len(silence_from)-self.fade_length, step_from):
            for b in range(0, len(silence_to)-self.fade_length, step_to):
                #get the range in the original scope
                rangeA = ((silence_range_a[0] + a), (silence_range_a[0] + (a + self.fade_length)))
                rangeB = ((silence_range_b[0] + b), (silence_range_b[0] + (b + self.fade_length)))
                #target_drop_length = self.max_drop - self.min_drop
                distance = round(length_of_range(range_between_ranges(rangeA, rangeB)), -2) #round distance to nearest 100ms
                #filter out comparisons that aren't far enough apart
                if distance >= self.min_drop*1000 and distance <= self.max_drop*1000:
                    silenceA = range_to_segment(sound, rangeA)
                    silenceB = range_to_segment(sound, rangeB)
                    score = compare_audio_segments(silenceA, silenceB)
                    matches.append(self.Match(rangeA, rangeB, score))
        return matches

    def get_matched_silences(self):
        """detect silences in the audio segment, compare, score for similarities."""
        matches = []
        silences = self.detect_silence(self.processed, min_silence_len=self.fade_length, silence_thresh=-21, seek_step=1)
        if len(silences) == 0:
            return matches
        if silences[0][0] == 0:
            silences.pop(0)
        if silences[len(silences)-1][1] == len(self.processed):
            silences.pop(len(silences)-1)
        for a, b in self.valid_silences(silences):
            matches += self.scan_silence(self.processed,a,b)
        return sorted(matches, key=lambda match: match.score)

    def get_first_nonsilent(self, sound, silence_threshold=-28):
            non_silences = silence.detect_nonsilent(sound, min_silence_len=self.fade_length,
                                                    silence_thresh=silence_threshold,seek_step=1)
            return non_silences[0]

    def detect_silence(self, audio_segment, min_silence_len=1000, silence_thresh=-16, seek_step=1):
        """Slightly altered version of the pydub native function.
            Examine audio segment for places where amplitude falls below threshold for longer than minimum silence.
            :return list of ranges (from_ms, to_ms)"""
        seg_len = len(audio_segment)

        # you can't have a silent portion of a sound that is longer than the sound
        if seg_len < min_silence_len:
            return []

        # convert silence threshold to a float value (so we can compare it to rms)
        silence_thresh = db_to_float(silence_thresh) * audio_segment.max_possible_amplitude

        # find silence and add start and end indicies to the to_cut list
        silence_starts = []

        # check successive (1 sec by default) chunk of sound for silence
        # try a chunk at every "seek step" (or every chunk for a seek step == 1)
        last_slice_start = seg_len - min_silence_len
        slice_starts = range(0, last_slice_start + 1, seek_step)

        # guarantee last_slice_start is included in the range
        # to make sure the last portion of the audio is seached
        if last_slice_start % seek_step:
            slice_starts = itertools.chain(slice_starts, [last_slice_start])

        for i in slice_starts:
            audio_slice = audio_segment[i:i + min_silence_len]
            if audio_slice.max <= silence_thresh:
                silence_starts.append(i)

        # short circuit when there is no silence
        if not silence_starts:
            return []

        # combine the silence we detected into ranges (start ms - end ms)
        silent_ranges = []

        prev_i = silence_starts.pop(0)
        current_range_start = prev_i

        for silence_start_i in silence_starts:
            continuous = (silence_start_i == prev_i + 1)

            # sometimes two small blips are enough for one particular slice to be
            # non-silent, despite the silence all running together. Just combine
            # the two overlapping silent ranges.
            silence_has_gap = silence_start_i > (prev_i + min_silence_len)

            if not continuous and silence_has_gap:
                silent_ranges.append([current_range_start,
                                      prev_i + min_silence_len])
                current_range_start = silence_start_i
            prev_i = silence_start_i

        silent_ranges.append([current_range_start,
                              prev_i + min_silence_len])

        return silent_ranges

class SilenceAudioWeight():

    def __init__(self, silence_processor):
        self.processor = silence_processor
        self.silences = self.processor.detect_silence(self.processor.processed, min_silence_len=self.processor.fade_length, silence_thresh=-21, seek_step=1)
        print self.silences
        self.valid = None
        first_nonsilent = self.processor.get_first_nonsilent(self.processor.processed)
        self.valid = [s for s in self.silences if s[0] > first_nonsilent[0]]
        print self.valid

    def frame_in_range(self, i, range):
        return range[0] < i < range[1]

    def __call__(self, i=0.0, j=0.0):
        if self.valid == None:
            return 1
        good_match = [s for s in self.valid if self.frame_in_range(i, s) or self.frame_in_range(j,s)]
        if len(good_match) == 2:
            return 1
        elif len(good_match) == 1:
            if self.frame_in_range(i,good_match[0]) and self.frame_in_range(j,good_match[0]):
                return 1
            else:
                return 5
        return 5