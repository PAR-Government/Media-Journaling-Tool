"""
Andrew Smith
PAR Government Systems
7/1/2016
JPEG compression w/ quantization table selection
7/7/16: Added thumbnail functionality. Thumbnail will be added to header.
7/11/16: Added functionality to specify Thumbnail with --thumb command on run.
"""
import argparse
import os
import sys
from collections import Counter, defaultdict
from PIL import Image
import numpy as np
import pyexiv2

# define database of quantization tables
Q_DIR = "QuantizationTables"
HELP = Q_DIR + "/help.txt"

def fnf_help():
    """
    Runs when desired camera q file can't be found. Ends with program exit.
    """
    usr = raw_input('Cannot find any instances of user keywords. '
                    'Type help for help, anything else to quit.\n')
    if usr.lower() == 'help':
        f = open(HELP, 'r')
        helpMsg = f.read()
        print helpMsg
        f.close()
    sys.exit()

def parse_q_tables(table_file):
    """
    Parses text file into quantization table usable by pil
    :param table_file: filename containing 16rows x 8cols of ints
    :return: list of lists representing quantization y and c quant tables
    """
    # split out 8x16 (16 rows, 8 cols) array into Luminance and Chrominance tables
    table = np.genfromtxt(Q_DIR + "/" + table_file).astype(int)
    yTable = table[:8,:].ravel().tolist()
    cTable = table[8:16,:].ravel().tolist()
    return [yTable, cTable] # list of lists

def reduce_matches(keywords):
    """
    Narrows down possible quantization tables based on user keywords (lowercase)
    :param keywords: User-input keywords describing camera
    :return: List of most likely matches
    """
    possibleFiles = []
    for qFileName in os.listdir(Q_DIR):
        for word in keywords:
            if word in qFileName.lower():
                possibleFiles.append(qFileName)
    if not possibleFiles:
        fnf_help()

    # tally each time a file appears
    counts = Counter(possibleFiles)

    # "reverse" dictionary, e.g. {4: [Canon 5D, Canon 5D III]...}
    matches = defaultdict(list)
    for k, v in counts.iteritems():
        matches[v].append(k)

    return matches[max(matches.keys(), key=int)]

def find_best_match(matches):
    """
    Reduces shortlist of q tables matches down to a best match and its thumbnail
    :param matches: list of keyword matches
    :return: best match
    """
    matches_tpremoved = [x for x in matches if (('thumbnail' not in x) or
                                                ('preview' not in x))]
    bestMatch = min(matches_tpremoved, key=len)

    thumbs = [x for x in matches if 'thumbnail' in x]
    if thumbs == []:
        bestThumb = bestMatch
    else:
        bestThumb = min(thumbs, key=len)

    return bestMatch, bestThumb

def insert_thumbnail(image_file, thumbnail_image_file, thumbnail_table_file):
    """
    Inserts specified thumbnail image file into base image file
    :param image_file: original image
    :param thumbnail_image_file: image file that will be inserted as thumbnail
    :param thumbnail_table_file: thumbnail jpg quantization tables
    """

    # parse q table
    thumb_table = parse_q_tables(thumbnail_table_file)

    # create thumbnail
    thumb = Image.open(thumbnail_image_file)
    thumb.thumbnail((128,128))
    thumb.save('thumb.jpg', qtables=thumb_table)
    thumb.close()

    # insert thumbnail into jpeg header
    metadata = pyexiv2.ImageMetadata(image_file)
    metadata.read()
    metadata.exif_thumbnail.erase()
    metadata.exif_thumbnail.set_from_file('thumb.jpg')
    metadata.write()

    # delete temp thumbnail file
    os.remove('thumb.jpg')

def save_jpg(image_file, output_file, image_table_file):
    """
    Performs the custom saving routine
    :param image_file: filename of image to resave
    :param output_file: output image filename
    :param image_table_file: filename of image q table
    :param thumbnail_tables: filename of thumbnail q table
    """

    # parse quantization tables
    image_table = parse_q_tables(image_table_file)

    # write jpeg with specified tables
    im = Image.open(image_file)
    im.save(output_file, subsampling=1, qtables=image_table)
    im.close()

def main():
    # parse cmd line args
    parser = argparse.ArgumentParser()
    parser.add_argument("image_fname", help="input image to convert to JPG")
    parser.add_argument("cam", help="camera model keywords to search in database")
    parser.add_argument('--thumb', nargs='?', default=False)
    args = parser.parse_args()
    outName, ext = os.path.splitext(args.image_fname)
    if ext.lower() == '.jpg':
        outName += '_recompressed'
    outName = outName + '.jpg'


    # find best match based on keywords
    camera = [x.lower() for x in args.cam.split('_')]
    matches = reduce_matches(camera)
    [bestMatchTable, thumbnailTable] = find_best_match(matches)
    if not all([x in bestMatchTable.lower() for x in camera]):
        fnf_help()


    print("Quantization Table Used: " + bestMatchTable)
    print("Thumbnail Table Used: " + thumbnailTable)

    save_jpg(args.image_fname, outName, bestMatchTable)

    if args.thumb:
        insert_thumbnail(outName, args.thumb, thumbnailTable)
        print 'Inserted a thumbnail'
    else:
        print 'No thumbnail inserted'

    print 'Done. Saved as: ' + outName


if __name__ == '__main__':
    main()