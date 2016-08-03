"""
Andrew Smith
PAR Government Systems
7/6/2016

add_meta adds exif metadata tags to an image
Does not currently support:
Exif Rational metadata types give weird results (may be due to outdated API)

Updated 7/8/2016 3:27PM
"""
import argparse
import sys
import datetime
import pyexiv2

def edit_tags(metadata, userTags):
    metadata.read()
    for tag in userTags:

        # metadata types are picky about what input they weill accept.
        # There is no way to tell what type of input a tag requires unless
        # it has been set already. So try/except is the way to go...
        try:
            if tag.startswith('Xmp'):
                metadata[tag] = userTags[tag]
                print('Inserted ' + userTags[tag] + ' into ' + tag)
            else:
                try:
                    metadata[tag] = [userTags[tag]]
                    print('Inserted ' + userTags[tag] + ' into ' + tag)

                except ValueError:
                    try:
                        metadata[tag] = [int(userTags[tag])]
                        print('Inserted ' + userTags[tag] + ' into ' + tag)
                    except ValueError:
                        try:
                            metadata[tag] = [pyexiv2.Rational.from_string(userTags[tag])]
                            print('Inserted ' + userTags[tag] + ' into ' + tag)
                        except ValueError:
                            try:
                                # assume value is either a date or a time
                                descr = map(int, userTags[tag].split(','))
                                metadata[tag] = [datetime.date(*tuple(descr))]
                                print('Inserted ' + userTags[tag] + ' into ' + tag)
                            except ValueError:
                                try:
                                    metadata[tag] = [datetime.time(*tuple(descr))]
                                    print('Inserted ' + userTags[tag] + ' into ' + tag)
                                except TypeError:
                                    print('Invalid Value for this tag: ' + str(userTags[tag]) +
                                          '. Check input formatting. No changes were made.')
                                    sys.exit()

        except KeyError:
            print('Invalid Tag: ' + tag + '. No metadata changes were made.')
            sys.exit()

    metadata.write(preserve_timestamps=True)

def main():
    # parse cmd line args
    parser = argparse.ArgumentParser()
    parser.add_argument('image_fname', help="input image to edit metadata")
    parser.add_argument('--tags', nargs='+', help="tag name and description")
    args = parser.parse_args()

    # change tags
    metadata = pyexiv2.ImageMetadata(args.image_fname)
    user_tags = dict(zip(args.tags[0::2], args.tags[1::2]))
    edit_tags(metadata, user_tags)

if __name__ == '__main__':
    main()
