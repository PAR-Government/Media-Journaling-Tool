from hp_data import *
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', '--dir',              default=os.getcwd(),            help='Specify directory')
    parser.add_argument('-R', '--recursive',        action='store_true',            help='Operate on subdirectories')
    parser.add_argument('-f', '--files',                                            help='Specify certain files')
    parser.add_argument('-r', '--range',                                            help='Specify range of files')
    parser.add_argument('-m', '--metadata',         default='metadata.txt',         help='Specify metadata txt file')
    parser.add_argument('-X', '--extraMetadata',    nargs='+',                      help='Additional non-standard metadata')
    parser.add_argument('-K', '--keywords',         nargs='+',                      help='Keywords for later searching')
    parser.add_argument('-S', '--secondary',        default=os.getcwd(),            help='Secondary storage location for copies')
    parser.add_argument('-P', '--preferences',      default='preferences.txt',      help='User preferences file')
    parser.add_argument('-A', '--additionalInfo',   default='',                     help='User preferences file')
    parser.add_argument('-B', '--s3Bucket',         default ='',                    help='S3 bucket/path')

    parser.add_argument('-T', '--rit',              action='store_true',            help='Produce output for RIT')
    parser.add_argument('-i', '--id',               default='',                     help='Camera serial #')
    parser.add_argument('-o', '--lid',              default='N/A',                  help='Local ID no. (cage #, etc.)')
    parser.add_argument('-L', '--lens',             default='',                     help='Lens serial #')
    parser.add_argument('-H', '--hd',               default='N/A',                  help='Hard drive location letter')
    parser.add_argument('-s', '--sspeed',           default='',                     help='Shutter Speed')
    parser.add_argument('-N', '--fnum',             default='',                     help='f-number')
    parser.add_argument('-e', '--expcomp',          default='',                     help='Exposure Compensation')
    parser.add_argument('-I', '--iso',              default='',                     help='ISO')
    parser.add_argument('-n', '--noisered',         default='',                     help='Noise Reduction')
    parser.add_argument('-w', '--whitebal',         default='',                     help='White Balance')
    parser.add_argument('-k', '--kvalue',           default='N/A',                  help='KValue')
    parser.add_argument('-E', '--expmode',          default='',                     help='Exposure Mode')
    parser.add_argument('-F', '--flash',            default='',                     help='Flash Fired')
    parser.add_argument('-a', '--autofocus',        default='',                     help='autofocus')
    parser.add_argument('-l', '--location',         default='N/A',                  help='location')
    args = parser.parse_args()

    # grab files
    imageList = []

    if args.files:
        imageList.extend(grab_individuals(args.files))
    elif args.range:
        fRange = args.range.split(' ')
        imageList.extend(grab_range(fRange))
    else:
        imageList.extend(grab_dir(args.dir, args.recursive))
    print 'Successfully grabbed images'

    print 'Collecting image data, this will take time for large amounts of images...'
    imageInfo = parse_image_info(imageList, args.id, args.lid, args.lens, args.hd, args.sspeed, args.fnum,
                            args.expcomp, args.iso, args.noisered, args.whitebal, args.expmode, args.flash,
                            args.autofocus, args.kvalue, args.location)
    print 'Successfully built image info!'

    if args.rit:
        csv_rit = os.path.join(args.dir, 'rit.csv')
        build_rit_file(imageList, imageInfo, csv_rit)

    # write final csv
    csv_tally = os.path.join(args.dir, 'tally.csv')
    tally_images(imageInfo, csv_tally)
    print 'Successfully tallied image data'

if __name__ == '__main__':
    main()