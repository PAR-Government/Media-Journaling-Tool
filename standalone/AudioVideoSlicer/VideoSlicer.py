import maskgen.algorithms.optical_flow
import argparse
import os
from maskgen.tool_set import getMilliSecondsAndFrameCount, getDurationStringFromMilliseconds
from maskgen.algorithms.optical_flow import smartDropFrames,get_best_frame_pairs
import maskgen.algorithms.drop_strategy as dropStrats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', help='The input video',required=True)
    parser.add_argument('--drop', help='Drop the ideal frames from the input video', action='store_true',required=False)
    parser.add_argument('--printf',help='Print the ideal frames to the console', action='store_true',required=False)
    parser.add_argument('--add',help='drop and add the ideal frames to the input video', action='store_true',required=False)
    parser.add_argument('--audio',help='Whether or not to consider the audio', action='store_true',required=False)
    parser.add_argument('-o',help='The desired output video path/name', required=False,default='out.avi')
    parser.add_argument('-sd', '--seconddrop', help='Seconds to drop', required=True)
    parser.add_argument('-sf', '--startframe', help='Number of frames to skip in the biginning of the video', required=True)
    args = parser.parse_args()
    out = args.o if not args.add else 'drop.avi'
    if args.audio:
        ar = {'Start Time': args.startframe, 'seconds to drop': args.seconddrop, 'audio': args.audio, 'drop':args.drop}
        dropre = transformDrop(None, args.i, out, **ar)
        if args.printf:
            if not args.drop:
                print("Optimal Frames:({}, {})".format(dropre[0][0], dropre[0][1]))
                print("Suggested Frames to Add:({})".format(dropre[0][2]))
                for x in range(1,len(dropre)):
                    print("Optimal Frames rank {} :({}, {})".format( x+1,dropre[x][0], dropre[x][1]))
            else:
                dropre = dropre[0]
                print("Optimal Frames:({}, {})".format(dropre['Start Time'], dropre['End Time']))
                print("Suggested Frames to Add:({})".format(dropre['Frames to Add']))
    if (args.printf or args.drop or args.add) and not args.audio:
        ar = {'Start Time': args.startframe, 'seconds to drop': args.seconddrop, 'drop':args.drop}
        dropre = transformDrop(None,args.i,out,**ar)[0]
        if args.printf:
            print("Optimal Frames:({}, {})".format(dropre['Start Time'],dropre['End Time']))
            print("Suggested Frames to Add:({})".format(dropre['Frames to Add']))
    if args.add:
        ar = {'Start Time': dropre['Start Time'],'Frames to Add':dropre['Frames to Add']}
        addre = transformAdd(None,out,args.o,**ar)
        if not args.drop:
            os.remove(out)

def transformDrop(img,source,target,**kwargs):
    start_time = getMilliSecondsAndFrameCount(str(kwargs['Start Time'])) if 'Start Time' in kwargs else (0, 1)
    end_time = getMilliSecondsAndFrameCount(str(kwargs['End Time'])) if 'End Time' in kwargs else None
    seconds_to_drop = float(kwargs['seconds to drop']) if 'seconds to drop' in kwargs else 1.0
    save_histograms = (kwargs['save histograms'] == 'yes') if 'save histograms' in kwargs else False
    drop = (kwargs['drop']) if 'drop' in kwargs else True
    codec = (kwargs['codec']) if 'codec' in kwargs else 'XVID'
    audio = (kwargs['audio']) if 'audio' in kwargs else False
    if drop:
        start, stop, frames_to_add = smartDropFrames(source, target,
                                                     start_time,
                                                     end_time,
                                                     seconds_to_drop,
                                                     savehistograms=save_histograms,
                                                     codec=codec,
                                                     audio=audio)
        # start = 1235
        # stop = 1245
        # frames_to_add=7
        return {'Start Time': str(start),
                'End Time': str(stop),
                'Frames Dropped': stop - start + 1,
                'Frames to Add': frames_to_add}, None
    if audio:
        frame_data = get_best_frame_pairs(source, target,
                                          start_time,
                                          end_time,
                                          seconds_to_drop,
                                          savehistograms=save_histograms,
                                          codec=codec,
                                          strategy=dropStrats.StratTopFrames)
    else:
        start, stop, frames_to_add = get_best_frame_pairs(source, target,
                                      start_time,
                                      end_time,
                                      seconds_to_drop,
                                      savehistograms=save_histograms,
                                      codec=codec,
                                      strategy=dropStrats.StratTopFramesVideo)

        return {'Start Time': str(start),
                'End Time': str(stop),
                'Frames Dropped': stop - start + 1,
                'Frames to Add': frames_to_add}, None

    # start = 1235
    # stop = 1245
    # frames_to_add=7
    return frame_data

def transformAdd(img,source,target,**kwargs):
    start_time = getMilliSecondsAndFrameCount(kwargs['Start Time']) if 'Start Time' in kwargs else (0, 1)
    end_time = getMilliSecondsAndFrameCount(kwargs['End Time']) if 'End Time' in kwargs else None
    frames_add = int(kwargs['Frames to Add']) if 'Frames to Add' in kwargs else None
    if frames_add is not None:
        end_time = (start_time[0], start_time[1] + frames_add - 1)
    codec = (kwargs['codec']) if 'codec' in kwargs else 'XVID'
    add_frames, end_time_millis = maskgen.algorithms.optical_flow.smartAddFrames(source, target,
                                                              start_time,
                                                              end_time,
                                                              codec=codec,
                                                              direction=kwargs['Direction'] if 'Direction' in kwargs else 'forward')

    if start_time[0] > 0:
        et = getDurationStringFromMilliseconds(end_time_millis)
    else:
        et = str(int(start_time[1]) + int(add_frames))

    return {'Start Time': str(kwargs['Start Time']),
            'End Time': et,
            'Frames to Add': int(add_frames),
            'Method': 'Pixel Motion',
            'Algorithm': 'Farneback',
            'scale': 0.8,
            'levels': 7,
            'winsize': 15,
            'iterations': 3,
            'poly_n': 7,
            'poly_sigma': 1.5,
            'Vector Detail': 100}, None

if __name__ == '__main__':
    main()
