import argparse
import os
import rawpy
import shutil
import sys
import itertools
from maskgen.image_wrap import ImageWrapper, openRaw

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d',  '--dir', required=True, help='File of projects')
    parser.add_argument('-r', '--result', required=True, help='File of projects')
    args = parser.parse_args()
    for item in os.listdir(args.dir):
        sourceName = os.path.join(args.dir, item)
        orig_outputName = os.path.join(args.result,item)
        params_list = []
        for i in itertools.product(['AAHD', 'DHT','VNG','MODIFIED_AHD','LINEAR','VCD_MODIFIED_AHD','LMMSE','PPG',None],
                                   ['camera', 'auto', None],
                                   ['XYZ','ProPhoto','default',None]):
            if i[1] is not None or i[2] is  not None:
                continue
            params = {'Bits per Channel':16}
            if (i[0] is not None):
                params['Demosaic Algorithm'] = i[0]
            #if (i[1] is not None):
            #    params['White Balance'] = i[1]
            #if (i[2] is not None):
            #    params['Color Space'] = i[2]
            tmpOutputName = item.split('.')[0] + '_' + str(i[0]) + '_' + str(i[1]) + '_' + str(i[2]) + '.png'
            outputName = os.path.join(args.result, tmpOutputName)
            params['outputname'] = outputName
            if os.path.exists(outputName):
                continue
            params_list.append(params)
        try:
            for name,im in openRaw(sourceName,args=params_list).iteritems():
                #outputName  = os.path.join(args.result, name)
                #shutil.move(name, outputName)
                print sourceName + '=>' + outputName
        except:
             print 'skipped ' + outputName
        if not os.path.exists(orig_outputName):
            print 'copying ' + sourceName
            shutil.move(sourceName, orig_outputName)
            sys.stdout.flush()

if __name__ == '__main__':
    main()
