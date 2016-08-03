"""
Andrew Smith
PAR Government Systems
Function to copy one image's metadata to another via command line

Be careful - all original metadata in target image is removed

Function call:
python copy_metadata <source_image> <target_image>
"""
import argparse
import pyexiv2

def copy(im1, im2):
    """
    Copies metadata from im1 to im2
    :param im1: string containing image1 filename
    :param im2: string containing image2 filename
    """
    meta1 = pyexiv2.ImageMetadata(im1)
    meta2 = pyexiv2.ImageMetadata(im2)

    meta1.read()
    meta2.read()

    meta1.copy(meta2)
    meta2.write(preserve_timestamps=True)

def main():

    # parse command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('image_1', help="image to take metadata FROM")
    parser.add_argument('image_2', help="image to insert metadata INTO")
    args = parser.parse_args()

    copy(args.image_1, args.image_2)


if __name__ == '__main__':
    main()