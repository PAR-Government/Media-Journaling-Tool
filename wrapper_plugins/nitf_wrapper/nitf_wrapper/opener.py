from nitf import *
from PIL import Image
import numpy as np

def openNTFFile(filename, isMask=None, args=None):
    select_band = args['band'] if 'band' in args else None
    select_image = args['image'] if 'image' in args else 0
    handle = IOHandle(filename)
    reader = Reader()
    record = reader.read(handle)
    images = record.getImages()
    if len(images) >= select_image:
        select_image = len(images) - 1
    imageReader = reader.newImageReader(select_image)
    subheader = images[select_image].subheader
    window = SubWindow()
    window.numRows = subheader['numRows'].intValue()
    window.numCols = subheader['numCols'].intValue()
    window.bandList = range(subheader.getBandCount())
    nbpp = subheader['numBitsPerPixel'].intValue()
    bandData = imageReader.read(window)
    channels = None
    if select_band is None:
        channels = np.zeros((window.numCols, window.numRows, subheader.getBandCount()),dtype=np.uint8)
    for band, data in enumerate(bandData):
        imdata = np.asarray(Image.frombuffer('L', (window.numCols, window.numRows), data, 'raw', 'L', 0, 1))
        if band == select_band:
            return imdata
        elif channels is not None:
            channels[:,:,band]  = imdata.astype('uint8')
    return channels
