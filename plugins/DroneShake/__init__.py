import numpy as np
import cv2
import random
from maskgen.cv2api import cv2api_delegate
from maskgen.video_tools import get_shape_of_video
import csv
import os
import logging

"""
Adding  random shaking params in order to make a synthetic video appear real
Potentially add the codec encoding to the params instead of guessing what the codec should be
"""


def transform(img, source, target, **kwargs):
    # image is not going to exist since this is used for video
    # source is the path to the video
    csvFile = None

    try:
        vid = cv2api_delegate.videoCapture(source)
        # Set the height and width of the new final frame
        pixelHeight = int(kwargs['height'])
        pixelWidth = int(kwargs['width'])

        width = int(vid.get(cv2api_delegate.prop_frame_width))
        height = int(vid.get(cv2api_delegate.prop_frame_height))

        if height == 0 or width == 0:
            print "Size of input video not received"
        cornerX = (width - pixelWidth) / 2
        cornerY = (height - pixelHeight) / 2

        out = cv2api_delegate.videoWriter(target, 0, int(kwargs['fps']), (pixelWidth, pixelHeight))
        csvData = []

        csvFile = os.path.splitext(source)[0] + '.csv'
        with open(csvFile, 'w+') as c:  #opens the csvfile that will contain the x and y crop corner
            writer = csv.writer(c, delimiter=',')
            """
            Goes through each frame individually and offsets it between -1 and 1 pixels (could be 0)
            Checks the new top-left corner coordinates to make sure it is valid 
            """

            while(True):
                try:
                    ret, frame = vid.read()
                    # print frame
                    x = None
                    if isinstance(frame, type(x)):
                        break
                    elif frame.all() == None:
                        break
                    elif frame.any() == None:
                        break
                    #  randomize the amt of movement + direction here to calculate new top left corner (X,Y)
                    ranX = random.randint(-1, 1)
                    ranY = random.randint(-1, 1)
                    cornerX += ranX
                    cornerY += ranY

                    """
                    Checks if the new top left corner will be within the bounds of the original frame
                    if not the a valid start corner, then it will move in the opposite direction
                    """
                    if cornerX + pixelWidth > width or cornerX < 0:
                        cornerX = cornerX - ranX
                        cornerX = cornerX + (-1 * ranX)

                    if cornerY + pixelHeight > height or cornerY < 0:
                        cornerY = cornerY - ranY
                        cornerY = cornerY + (-1 * ranY)

                    x = cornerX
                    y = cornerY

                    csvData.append([x, y])  # Add data to the csvData array to print later to csvfile

                    """
                       Crops to specific height and width starting at specific x and y coordinates
                    """
                    cv_image = np.asarray(frame)
                    final = cv_image[y:(pixelHeight + y), x:(pixelWidth + x), :]
                    out.write(final)

                except Exception as e:
                    break
            for row in csvData:
                writer.writerow(row)  #writes the data of cropping per frame to the csvfile
        vid.release()
        out.release()
    except Exception as e:
        logging.getLogger('maskgen').warning(e.message)
    return {'output_files':{'crop_locations_file': csvFile, 'Approach': 'Crop'}}, None


def operation():
    return {
        'category': 'AdditionalEffect',
        'name': 'CameraMovement',  # Drone?
        'description': 'Adds a shaking effect to the video to make it appear real rather than synthetic',
        'software': 'OpenCV',
        'version': cv2.__version__,
        'arguments': {
            'fps': {'type': "double[0:100000]", 'description': 'Frames per Second'},
            'height': {'type': "int[0:100000]", 'description': 'Height of the output video'},
            'width': {'type': "int[0:100000]", 'description': 'Width of the output video'},
        },
        'transitions': [
            'video.video'
        ]
    }


def suffix():
    return '.avi'