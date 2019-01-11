from maskgen import maskgen_audio, tool_set
from maskgen.tool_set import VidTimeManager
import optical_flow
import os

class DropStrategy(object):
    def __init__(self,in_file,out_file,fps,start,codec):
        self.in_file = in_file
        self.out_file = out_file
        self.fps = fps
        self.start = start
        self.codec = codec

    def getWeighter(self):
        return lambda x,y: 1

    def drop(self, firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches):
        time_manager = VidTimeManager(startTimeandFrame=(0, firstFrametoDrop),
                                      stopTimeandFrame=(0, lastFrametoDrop))
        optical_flow.createOutput(self.in_file, self.out_file, time_manager, codec=self.codec)
        return firstFrametoDrop, lastFrametoDrop, framesToAdd

class StratVideo(DropStrategy):
    def __init__(self, in_file, out_file, fps, start, codec):
        DropStrategy.__init__(self, in_file, out_file, fps, start, codec)

    def getWeighter(self):
        return super(StratVideo, self).getWeighter()

    def drop(self, firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches):
        return super(StratVideo, self).drop(firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches)


class StratAudioSep(StratVideo):
    def __init__(self,in_file,out_file,fps,start,codec):
        super(StratAudioSep,self).__init__(in_file,out_file,fps,start,codec)
        self.sp = maskgen_audio.SilenceProcessor(in_file)


    def getWeighter(self):
        #self.sp = maskgen_audio.SilenceProcessor(self.in_file)
        return optical_flow.silenceWeighter(self.fps,self.sp,self.start).value

    def drop(self, firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches):
        super(StratAudioSep, self).drop(firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches)
        st = tool_set.getMilliSecondsAndFrameCount(int(firstFrametoDrop), self.fps)[0]
        en = tool_set.getMilliSecondsAndFrameCount(int(lastFrametoDrop), self.fps)[0]
        audio_file = maskgen_audio.cut_n_stitch(self.sp.original, [int(st), int(en)], 100)
        maskgen_audio.export_audio(audio_file, os.path.splitext(self.out_file)[0] + '.wav')
        return firstFrametoDrop, lastFrametoDrop, framesToAdd

class StratAudVidSelect(StratAudioSep):
    def __init__(self,in_file,out_file,fps,start,codec):
        super(StratAudVidSelect, self).__init__(in_file, out_file, fps, start, codec)

    def drop(self, firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches):
        st = tool_set.getMilliSecondsAndFrameCount(int(firstFrametoDrop), self.fps)[0]
        en = tool_set.getMilliSecondsAndFrameCount(int(lastFrametoDrop), self.fps)[0]
        return firstFrametoDrop, st, lastFrametoDrop, en, framesToAdd

class StratAudVidTogether(StratAudioSep):
    def __init__(self,in_file,out_file,fps,start,codec):
        super(StratAudVidTogether, self).__init__(in_file, out_file, fps, start, codec)

    def drop(self, firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches):
        results = super(StratAudVidTogether, self).drop(firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches)
        # Code that conjoins the stuff that I'm not sure about yet
        # ffmpeg -i vid -i aud -c copy outvid
        import maskgen.ffmpeg_api as ffmpeg
        tmpvid = os.path.splitext(self.out_file)[0] + 'tmp' + os.path.splitext(self.out_file)[1]
        os.rename(self.out_file,tmpvid)
        ffmpeg.run_ffmpeg(['-i',tmpvid,'-i',os.path.splitext(self.out_file)[0] + '.wav','-c:v', 'rawvideo','-c:a', 'pcm_s32le', '-r', str(self.fps),
                           self.out_file, '-y'])
        os.remove(tmpvid)
        os.remove(os.path.splitext(self.out_file)[0] + '.wav')
        return results

class StratTopFrames(StratAudVidSelect):
    def __init__(self,in_file,out_file,fps,start,codec):
        super(StratTopFrames,self).__init__(in_file,out_file,fps,start,codec)

    def drop(self, firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches):
        #results = super(StratTopFrames, self).drop(firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches)
        match = []
        match.append(tuple([firstFrametoDrop,lastFrametoDrop,framesToAdd]))
        bestIndecies = flows.argsort()[1:10]
        for i in bestIndecies:
            ffd = matches[i][0] + self.start + 2
            lfd = matches[i][1] + self.start
            match.append(tuple([ffd,lfd]))
        return match

class StratTopFramesVideo(StratAudVidSelect):
    def __init__(self,in_file,out_file,fps,start,codec):
        super(StratTopFramesVideo,self).__init__(in_file,out_file,fps,start,codec)

    def getWeighter(self):
        return lambda x,y: 1

    def drop(self, firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches):
        #results = super(StratTopFrames, self).drop(firstFrametoDrop, lastFrametoDrop, framesToAdd, flows, matches)
        match = []
        match.append(tuple([firstFrametoDrop,lastFrametoDrop,framesToAdd]))
        return firstFrametoDrop,lastFrametoDrop,framesToAdd
