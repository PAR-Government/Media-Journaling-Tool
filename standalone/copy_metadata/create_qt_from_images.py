# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
from maskgen.plugins import  loadPlugins,callPlugin
from maskgen.image_wrap import openImageFile
from maskgen.jpeg.utils import get_subsampling, parse_tables, sort_tables, check_rotate
from maskgen.exif import getexif
import os

def dumpTable(filename, tableData):

    with open(filename,'w') as tableDataFp:
        count = 0
        for table in tableData:
            for item in table:
                tableDataFp.write('{}'.format(item))
                count += 1
                if count % 8 == 0:
                    tableDataFp.write('\n')
                else:
                    tableDataFp.write('\t')

avoidkeys = set(['-System:FileModifyDate',
                '-Composite:SubSecCreateDate',
                '-System:FileInodeChangeDate',
                '-System:Directory',
                '-System:FilePermissions',
                '-System:FileAccessDate',
                '-Composite:ImageSize',
                '-System:FileName',
                '-ExifIFD:CreateDate',
                '-Sony:SonyDateTime']
                )
computekeys = ['Date','Time','Width','Height']

def writeExif(filename,exifdata):
    with open(filename,'w') as fp:
        for k, v in exifdata.iteritems():
            if k not in avoidkeys:
                iscompute=len([computekey for computekey in computekeys if k.find(computekey) >= 0 ]) > 0
                linetype = 'compute' if iscompute else 'database'
                fp.write('{},{},{}\n'.format(linetype,k,v))



def  main():
    files_to_qt = {
        "iPhone6s.jpg":"iPhone6s-[{}x{}]-{}.txt",
        "Galaxy_S4.jpg": "Samsung-Galaxy-S4-[{}x{}]-{}.txt",
        "NEX-5TL.jpg": "Sony-NEX-5TL-[{}x{}]-{}.txt",
        "droid_maxx.jpg": "Motorola-Droid-Maxx-[{}x{}]-{}.txt",
        "canon_eos_sl1.jpg": "Canon-EOS-SL1-[{}x{}]-{}.txt",
        "Kodak_M1063_0_9367.JPG": "Kodak-EasyShare-M1063-[{}x{}]-{}.txt",
        "Samsung_L74wide_1_44105.JPG": "Samsung-Digimax-L74_Wide-[{}x{}]-{}.txt",
        "Praktica_DCZ5.9_3_35003.JPG": "Praktica-DCZ-59-[{}x{}]-{}.txt",
        "Olympus_mju_1050SW_0_23680.JPG": "Olympus-Stylus-1050SW-[{}x{}]-{}.txt",
        "Panasonic_DMC-FZ50_0_26019.JPG": "Panasonic-DMC-FZ50-[{}x{}]-{}.txt"
    }

    imagedir = ''
    savedir = 'maskgen/plugins/JpgFromCamera/QuantizationTables'
    for file_name_prefix in files_to_qt:
        filename = os.path.join(imagedir,file_name_prefix)
        thumbTable  = None
        prevTable = None
        finalTable = None
        tables_zigzag = parse_tables(filename)
        tables_sorted = sort_tables(tables_zigzag)
        if len(tables_sorted) == 6:
            thumbTable = tables_sorted[0:2]
            prevTable = tables_sorted[2:4]
            finalTable = tables_sorted[4:6]
        elif len(tables_sorted) > 2 and len(tables_sorted) < 6:
            thumbTable = tables_sorted[0:2]
            finalTable = tables_sorted[-2:]
        else:
            finalTable = tables_sorted

        im = openImageFile(filename)
        outfilenametemplate = files_to_qt[file_name_prefix]
        dims = im.size
        if thumbTable is not None:
            dumpTable(os.path.join(savedir,outfilenametemplate.format(dims[0],dims[1],'thumbnail')),
                      thumbTable)
        if prevTable is not None:
            dumpTable(os.path.join(savedir, outfilenametemplate.format(dims[0], dims[1], 'preview')),
                      prevTable)
        if finalTable is not None:
            dumpTable(os.path.join(savedir, outfilenametemplate.format(dims[0], dims[1], 'QT')),
                      finalTable)
        writeExif(os.path.join(savedir, outfilenametemplate.format(dims[0], dims[1], 'metadata')),
                  getexif(filename,args=['-args', '-G1','-n'],separator='='))


if __name__ == '__main__':
    main()