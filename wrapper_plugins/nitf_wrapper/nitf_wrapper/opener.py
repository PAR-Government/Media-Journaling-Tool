from osgeo import gdal
import numpy as np

def openNTFFile(filename, isMask=None, args=None):
    import os
    print (os.path.exists(filename))
    drv = gdal.GetDriverByName('NITF')
    src_ds = gdal.Open(filename,gdal.GA_ReadOnly)
    select_band = args['band'] if args is not None and 'band' in args  else None
    select_image = args['image'] if args is not None and 'image' in args else 0
    to_rgb =  args is None or ('rgb' in args and args['rgb']=='yes')
    nXSize = src_ds.RasterXSize
    nYSize = src_ds.RasterYSize
    count = src_ds.RasterCount

    channels = None
    if select_band is None:
        data = np.array(src_ds.GetRasterBand(1).ReadAsArray())
        channels = np.zeros((nYSize, nXSize, count),dtype=np.uint8 if to_rgb else data.dtype)
        channels[:, :,0] = data
        for i in range(1,min(count,4)):
            data = np.array(src_ds.GetRasterBand(i+1).ReadAsArray())
            channels[:, :, i] = data.astype(channels.dtype)
    else:
        channels = np.array(src_ds.GetRasterBand(select_band).ReadAsArray())
    return channels, 'NITF'
