"""
Andrew Smith
PAR Government Systems
7/6/2016

change_all_metadata should read a text file for new metadata tags and values, and apply them to ALL images in the directory

Update 7/8/2016: Handle more metadata types
Update 7/12/2016: Allow for deletion of tags
Update 7/12/2016: Allow for command line args to specify metadata file (-m), and to purge metadata (-p)
Update 7/20/2016: Add args for specifying directory (-d) and subdirectories (-r)
"""
import os
import sys
import datetime
import argparse
import pyexiv2


def build_new_meta(data, purge):
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
                line = line.rstrip('\n')
                (tag, descr) = line.split('=')
                if purge:
                    newData[tag] = ''
                else:
                    newData[tag] = descr
    except IOError:
        print('Input file metadata.txt not found. '+
              'Please try again.')
        sys.exit()
    return newData

def grab_images(dir, recursive):
    """
    Puts desired image files into a list
    :param dir: (string) root directory of files
    :param recursive: (boolean) If true, search subdirectories as well
    :return: list of strings containing filepaths/names
    """
    imageList = []
    root = dir
    exts = ('.jpg', '.jpeg', '.jpe', '.tif', '.tiff')

    if recursive:
        for path, subdirs, files in os.walk(root):
            for fname in files:
                if fname.lower().endswith(exts):
                    imageList.append(os.path.join(path, fname))
    else:
        for fname in os.listdir(root):
            if fname.lower().endswith(exts):
                imageList.append(root + '\\' + fname)

    return imageList

def change_metadata(image, newData):
    """
    Open and write metadata for image
    :param image: (string) image file to change metadata
    :param newData: (dict) metadata tags
    """

    # pyexiv2 is very picky about what it allows as data in metadata tags
    # you also can't check a metadata type if it doesn't exist for an
    # image yet. Therefore, try-catches must be used to handle
    # various inputs.
    metadata = pyexiv2.ImageMetadata(image)
    metadata.read()
    try:
        for key in newData:
            if newData[key] == '':
                try:
                    del metadata[key]
                except KeyError:
                    # the user tried to delete a tag that doesn't exist.
                    # this is fine, just skip over it.
                    continue
            elif key.startswith('Xmp'):
                metadata[key] = newData[key]
            else:
                try:
                    metadata[key] = [newData[key]]
                except ValueError:
                    try:
                        metadata[key] = [int(newData[key])]
                    except ValueError:
                        try:
                            metadata[key] = [pyexiv2.Rational.from_string(newData[key])]
                        except ValueError:
                            try:
                                # assume value is either a date or a time
                                descr = map(int, newData[key].split(','))
                                metadata[key] = [datetime.date(*tuple(descr))]
                            except ValueError:
                                try:
                                    metadata[key] = [datetime.time(*tuple(descr))]
                                except TypeError:
                                    print('Invalid Value for this tag: ' + str(newData[key]) +
                                          '. Check input formatting. No changes were made.')
                                    sys.exit()
    except KeyError:
        print('The tag: ' + key + ' does not exist. Check input formatting. No changes were made.')
        sys.exit()
    metadata.write(preserve_timestamps=True)

def main():
    # parse cmd line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir',      default=os.getcwd(),    help='directory of images')
    parser.add_argument('-m', '--file',     default='metadata.txt', help='metadata txt file')
    parser.add_argument('-p', '--purge',    action='store_true',    help='remove all tags in file')
    parser.add_argument('-r', '--recursive',action='store_true',    help='operate on subdirectories')
    
    args = parser.parse_args()

    newData = build_new_meta(args.file, args.purge)

    # grab all jpg and tiff files in dir into a list
    imageList = grab_images(args.dir, args.recursive)

    # iterate over list
    for image in imageList:
        change_metadata(image, newData)

if __name__ == '__main__':
    main()