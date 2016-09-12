from subprocess import call
import argparse
import os
import sys

def parse_file(data, purge=False):
    """
    Builds dictionary of new metadata tags based on txt file
    :param data: (string) text file containing metadata changes
    :param purge: (boolean) If true, delete the tags specified in txt file
    :return: dict containing metadata tags and their new values
    """
    newData = {}
    # open text file
    try:
        with open(data) as f:
            for line in f:
                (tag, descr) = line.split('=')
                if purge:
                    newData[tag.lower().strip()] = ''
                else:
                    newData[tag.lower().strip()] = descr.strip()
    except IOError:
        print('Input file: ' + data + ' not found. ' + 'Please try again.')
        sys.exit()
    return newData

def process(dir, metadata, recursive=False, purge=False, quiet=False):
    exifToolInput = ['exiftool', '-progress']
    for key, value in metadata.iteritems():
        exifToolInput.append('-' + key + '=' + value)
    if recursive:
        exifToolInput.extend(('-XMPToolkit=', '-overwrite_original', '-r', '-L', '-m', '-P'))
    else:
        exifToolInput.extend(('-XMPToolkit=', '-overwrite_original', '-L', '-m', '-P'))

    if type(dir) is str:
        exifToolInput.append(dir)
    elif type(dir) is list:
        for item in dir:
            exifToolInput.append(item)

    if quiet:
        del exifToolInput[1]

    # run exiftool
    call(exifToolInput)

# def process(dir, metadata, recursive=False, purge=False, quiet=False):
#     exifToolInput = 'exiftool'
#     for key, value in metadata.iteritems():
#         exifToolInput += '-' + key + '=' + value + ' '
#     if recursive:
#         exifToolInput += '-XMPToolkit= -overwrite_original -r -L -m -P' + ' '.join(dir)
#         exifToolInput.extend(('-XMPToolkit=', '-overwrite_original', '-r', '-L', '-m', '-P', '-progress', ))
#     else:
#         exifToolInput += '-XMPToolkit= -overwrite_original -r -L -m -P' + ' '.join(dir)
#         exifToolInput.extend(('-XMPToolkit=', '-overwrite_original', '-L', '-m', '-P', '-progress', ' '.join(dir)))
#
#     if quiet:
#         del exifToolInput[-2]
#
#     # run exiftool
#     call(exifToolInput)


def main():
    # parse cmd line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', default=os.getcwd(), help='directory of images')
    parser.add_argument('-m', '--file', default='metadata.txt', help='metadata txt file')
    parser.add_argument('-p', '--purge', action='store_true', help='remove all tags in file')
    parser.add_argument('-r', '--recursive', action='store_true', help='operate on subdirectories')
    parser.add_argument('-q', '--quiet', action='store_true', help='will not show progress')

    args = parser.parse_args()

    # parse data
    newData = parse_file(args.file, args.purge)
    process(args.dir, newData, args.recursive)


if __name__ == '__main__':
    main()