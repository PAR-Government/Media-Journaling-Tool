"""
PAR Government Systems

Two TIFF images, and compresses the first with the configuration from the second

"""

from PIL import Image
import maskgen.exif


def check_rotate(im, jpg_file_name):
    return maskgen.exif.rotateAccordingToExif(im,maskgen.exif.getOrientationFromExif(jpg_file_name))

def tiff_save_as(source, target, donor_img, donor_file, rotate):
    """
    Saves image file using the same image compression
    :param source: string filename of source image
    :param target: string filename of target (result)
    :param donor: string filename of donor TIFF
    :param rotate: boolean True if counter rotation is required
    """
    im = Image.open(source)
    if rotate:
      im = check_rotate(im,donor_file)
    im.save(target, format='TIFF', **donor_img.info)
    width, height = im.size
    maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-XMPToolkit=', target])
    maskgen.exif.runexif(['-q', '-all=', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor_file, '-all:all', '-unsafe', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-XMPToolkit=',
                 '-ExifImageWidth=' + str(width),
                 '-ImageWidth=' + str(width),
                 '-ExifImageHeight=' + str(height),
                 '-ImageHeight=' + str(height),
                 target])
    im.close()


def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    rotate = 'rotate' in kwargs and kwargs['rotate'] == 'yes'
    tiff_save_as(source, target, donor[0],donor[1], rotate)
    
    return False,None
    
def operation():
    return ['AntiForensicExifQuantizationTable','AntiForensicExif',
            'Save as a TIFF using original tables and EXIF', 'PIL', '1.1.7']
    
def args():
    return [('donor', None, 'TIFF with donor EXIF'),
            ('rotate', 'yes', 'Answer yes if the image should be counter rotated according to EXIF Orientation')]

def suffix():
    return '.TIF'
