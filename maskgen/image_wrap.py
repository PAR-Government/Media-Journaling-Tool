from PIL import Image
import cv2
import numpy as np
import os
import subprocess
from pkg_resources import iter_entry_points
from cachetools import LRUCache
from cachetools import cached
from threading import RLock
import logging
import os

image_lock = RLock()
image_cache = LRUCache(maxsize=24)

try:
    from tifffile import TiffFile,imsave
except ImportError:
    def imsave(filename, img, **newargs):
        import scipy.misc
        scipy.misc.imsave(filename,img)
    class TiffFile:
        def __init__(self,filename):
            pass
        def __array__(self):
            return []
        def __exit__(self,x,y,z):
            return []
        def __enter__(self):
            return []

def openRaw(filename,isMask=False):
    try:
       import rawpy
       with rawpy.imread(filename) as raw:
           return ImageWrapper(raw.postprocess(), to_mask=isMask)
    except:
        return None


def openTiff(filename, isMask=False):
    raw = openRaw(filename,isMask=isMask)
    info = {}
    if filename.lower().find('tif') >= 0:
        try:
            with TiffFile(filename) as tiffdata:
                for page in tiffdata:
                    for tag in page.tags.values():
                        t, v = tag.name, tag.value
                        if t.startswith('compress'):
                            info['compress'] = v
        except:
            pass
        try:
            nonRaw = ImageWrapper(cv2.cvtColor(cv2.imread(filename, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGR2RGB), info=info,
                            to_mask=isMask)
            if raw is not None and raw.size[0] > nonRaw.size[0] and raw.size[1] > nonRaw.size[1]:
                return raw
            return nonRaw
        except:
            return raw
    return raw

def wand_image_extractor(filename,isMask=False):
    import PythonMagick
    im = PythonMagick.Image(filename)
    myPilImage = Image.new('RGB', (im.GetWidth(), im.GetHeight()))
    myPilImage.fromstring(im.GetData())
    return ImageWrapper(np.asarray(myPilImage), mode=myPilImage.mode, info=myPilImage.info,to_mask=isMask)

def pdf2_image_extractor(filename,isMask=False):
    import PyPDF2
    import io
    from PyPDF2 import generic
    with open(filename, "rb") as f:
        input1 = PyPDF2.PdfFileReader(f)
        page0 = input1.getPage(0)
        xObject = page0['/Resources']['/XObject'].getObject()
        for obj in xObject:
            if xObject[obj]['/Subtype'] == '/Image':
                size = (xObject[obj]['/Width'], xObject[obj]['/Height'])
                if xObject[obj]['/ColorSpace'] == '/DeviceRGB':
                    mode = "RGB"
                else:
                    mode = "P"
                hasJPEG = len([x for x in xObject[obj]['/Filter'] if x == '/DCTDecode']) > 0
                if  hasJPEG:
                    if type(xObject[obj]['/Filter']) == generic.ArrayObject:
                            xObject[obj].update({generic.NameObject('/Filter'):
                                            generic.ArrayObject( [x for x in xObject[obj]['/Filter']
                                                                  if x not in  ['/DCTDecode','/JBIG2Decode']])})
                    im = Image.open(io.BytesIO(bytearray(xObject[obj].getData())))
                    return ImageWrapper(np.asarray(im), mode=im.mode, info=im.info,to_mask=isMask)
    return None

def convertToPDF(filename,isMask=False):
    import platform
    prefix = filename[0:filename.rfind('.')]
    newname = prefix + '.png'
    if "Darwin" in platform.platform():
        if not os.path.exists(newname):
            with open(os.devnull, 'w') as fp:
                subprocess.call(['sips', '-s', 'format', 'png', filename, '--out', newname], stdout=fp)
    with open(newname, 'rb') as f:
        im = Image.open(f)
        im.load()
        return ImageWrapper(np.asarray(im), mode=im.mode, info=im.info,to_mask=isMask)
    return None

def getProxy(filename):
    proxyname = filename[0:filename.rfind('.')] +'_proxy.png'
    if os.path.exists(proxyname):
        return proxyname
    return None

def defaultOpen(filename,isMask=False):
    with open(filename, 'rb') as f:
        im = Image.open(f)
        im.load()
        if im.format == 'TIFF' and filename.lower().find('tif') < 0:
            raw = openTiff(filename, isMask=isMask)
            if raw is not None and raw.size[0] > im.size[0] and raw.size[1] > im.size[1]:
                return raw
    result = ImageWrapper(np.asarray(im), mode=im.mode, info=im.info, to_mask=isMask)
    return None if result.size == (0,0) else result

def proxyOpen(filename, isMask=False):
    proxyname = getProxy(filename)
    if proxyname is not None:
        return openImageFile(filename,isMask=isMask)
    return None

# openTiff supports raw files as well
file_registry = [('pdf', [pdf2_image_extractor,wand_image_extractor,convertToPDF]), ('', [defaultOpen]), ('', [openTiff]),('',[proxyOpen])]
file_write_registry = {}

for entry_point in iter_entry_points(group='maskgen_image', name=None):
    file_registry.insert(0,(entry_point.name,[entry_point.load()]))

for entry_point in iter_entry_points(group='maskgen_image_writer', name=None):
    file_write_registry[entry_point.name] =entry_point.load()

def getFromWriterRegistry(format):
    return file_write_registry[format] if format in file_write_registry else None

def openFromRegistry(filename,isMask=False):
    for suffixList in file_registry:
        if suffixList[0] in filename.lower():
            for func in suffixList[1]:
                try:
                    result = func(filename,isMask=isMask)
                    if result is not None and result.__class__ is not ImageWrapper:
                        result  = ImageWrapper(result[0],mode=result[1])
                    if result is not None and result.size != (0,0):
                        return result
                except Exception as e:
                    logging.getLogger('maskgen').info( 'Cannot to open image file ' + filename + ' with ' + str(func) + '...trying another opener.')
                    logging.getLogger('maskgen').info(str(e))
    return None

def filehashkey(*args, **kwargs):
    """Return a cache key for the specified hashable arguments."""
    return args[0]

def deleteImage(filename):
    with image_lock:
        if filename in image_cache:
             image_cache.pop(filename)

def openImageFile(filename,isMask=False):
    """
    :param filename:
    :param isMask:
    :return:
    @type filename: str
    @rtype: ImageWrapper
    """
    if not os.path.exists(filename):
        pos = filename.rfind('.')
        mod_filename = filename[0:pos] + filename[pos:].lower()
        if os.path.exists(mod_filename):
           filename = mod_filename
    if not os.path.exists(filename):
        raise ValueError("File not found: " + filename)

    current_time = os.stat(filename).st_mtime

    with image_lock:
        if filename in image_cache:
            wrapper, update_time = image_cache[filename]
            if current_time - update_time <= 0 and wrapper is not None:
                return wrapper

    wrap = openFromRegistry(filename, isMask=isMask)
    with image_lock:
        image_cache[filename] = (wrap, current_time)
    return wrap

def invertMask(mask):
    mask.invert()

def tofloat(img_array):
    if str(img_array.dtype).startswith('f'):
        return img_array
    oldtype = img_array.dtype
    img_array = img_array.astype('float32')
    img_array /= float(np.iinfo(oldtype).max)
    return img_array

def totype(img_array, type):
    if img_array.dtype == type  or type is None:
        return img_array
    if type == 'uint8':
        img_array = tofloat(img_array)
        img_array = img_array * np.iinfo(type).max
    return img_array.astype(type)

def get_mode(image_array):
    s = image_array.shape
    if len(s) == 2:
        hasBigValues = (image_array>1).any()
        return 'F' if str(image_array.dtype).startswith('f') and not hasBigValues else 'L'
    elif s[2] == 4:
        return 'RGBA'
    elif s[2] == 2:
        return 'LA'
    elif s[2] > 4 and image_array.dtype == 'uint8':
        return 'JP2'
    else:
        return 'RGB'

class ImageWrapper:
    """
    @type image_array: numpy.array
    """
    def __init__(self,image_array, mode=None, to_mask=False,info=None):
        if str(type(image_array)) == 'ImageWrapper':
            self.image_array = image_array.image_array
        else:
            self.image_array = image_array
        self.info = info
        self.mode = mode if mode is not None else get_mode(image_array)
        self.size = (image_array.shape[1],image_array.shape[0])
        if to_mask and self.mode != 'L':
            self.image_array = cv2.cvtColor(self.to_rgb(type='uint8').image_array,cv2.COLOR_RGBA2GRAY)
            self.mode = 'L'

    def has_alpha(self):
        return len(self.image_array.shape) == 3 and self.mode.find('A') > 0

    def to_image(self):
        return Image.fromarray(self.image_array,mode = self.mode)

    def toPIL(self):
        return Image.fromarray(self.to_rgb(type = 'uint8').to_array())

    def to_array(self):
        return np.copy(self.image_array)

    def apply_mask(self,mask):
        if mask is not None and len(self.image_array.shape) == 3:
            img = np.copy(self.image_array)
            mask_array = np.copy(np.asarray(mask))
            mask_array[mask_array>0] = 1
            for i in range(img.shape[2]):
                img[:, :, i] = img[:, :, i] * mask_array
            return ImageWrapper(img)
        return ImageWrapper(self.image_array)

    def apply_mask_rgba(self,mask):
        image = self.convert('RGBA')
        img = np.copy(image.image_array)
        mask_array = np.copy(np.asarray(mask))
        img[:, :, 3] = img[:, :, 3] * mask_array
        return ImageWrapper(self.image_array)

    def to_rgb(self, type=None):
        type = self.image_array.dtype if type is None else type
        s = self.image_array.shape
        img = self.convert('RGB')
        if self.mode.find('A') > 0:
            alpha = self.image_array[:,:,self.image_array.shape[2]-1]
            zeros = np.zeros((self.size[1],self.size[0]))
            zeros[alpha > 0] = 1
            img_array2 = np.zeros((self.image_array.shape[0],self.image_array.shape[1],3))
            for i in range(3):
                img_array2[:, :, i] = img.image_array[:, :, i] * zeros
            img_array2 = img_array2.astype(self.image_array.dtype)
            return ImageWrapper(totype(img_array2,type=type),mode='RGB')
        elif len(s) == 2:
             return ImageWrapper(cv2.cvtColor(totype(self.image_array,type),cv2.COLOR_GRAY2RGB),mode='RGB')
        return ImageWrapper(totype(np.copy(img.image_array),type))

    def touint8(self):
        if self.image_array.dtype == 'uint16':
            img_array = (self.image_array.astype('float')/65536.0)*256.0
            img_array = img_array.astype('uint8')
            self.image_array = img_array
        elif self.image_array.dtype == 'float':
            img_array = self.image_array * 256
            self.image_array = img_array.astype('uint8')


    def save(self, filename, **kwargs):
        if 'format' in kwargs:
            format = kwargs['format']
        elif getFromWriterRegistry(self.mode.lower()):
            format = self.mode.lower()
        else:
            format = 'PNG'
        format = 'TIFF' if self.image_array.dtype == 'uint16' else format
        newargs = dict(kwargs)
        newargs['format'] = format
        img_array = self.image_array
        file_writer = getFromWriterRegistry(format.lower())
        if file_writer is not None:
            file_writer(filename, img_array)
            return
        if self.mode == 'F':
            img_array =  img_array * 256
            img_array = img_array.astype('uint8')
        if img_array.dtype == 'uint8' or self.mode == 'L':
            if format == 'PDF' and self.mode != 'RGB':
                self.convert('RGB').save(filename,**newargs)
            else:
                Image.fromarray(img_array).save(filename,**newargs)
            return
        newargs.pop('format')
        imsave(filename, self.image_array,**newargs)
        if os.path.exists(filename):
            with image_lock:
                image_cache[filename] = (self,os.stat(filename).st_mtime)
        #flags =[(cv2.IMWRITE_JPEG_QUALITY,100)]if format in kwargs and format['kwargs'] == 'JPEG' else [(int(cv2.IMWRITE_PNG_COMPRESSION),0)]
        #cv2.imwrite(filename, self.image_array)
       # tiff = TIFF.open(filename,mode='w')
       # tiff.write_image(self.image_array)#,format='uint16')


    def load(self):
        pass

    def  __array__ (self):
        return self.image_array

    def convert(self, convert_type_str):
        if self.mode == convert_type_str:
            return self
        if self.mode == 'F':
            return ImageWrapper(np.asarray(Image.fromarray(self.image_array,mode='F').convert(convert_type_str)))
        img_array = (np.iinfo('uint8').max * self.image_array).astype('uint8') if str(self.image_array.dtype).startswith('f') else self.image_array
        if self.mode == 'JP2':
            img_array = img_array[:,:,0:4]
            return ImageWrapper(np.asarray(Image.fromarray(img_array, mode='RGBA').convert(convert_type_str)),
                                mode=convert_type_str)
        if img_array.dtype == 'uint8':
            return ImageWrapper(np.asarray(Image.fromarray(img_array,mode=self.mode).convert(convert_type_str)),mode=convert_type_str)
        if self.mode == 'RGB' and convert_type_str == 'RGBA':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_RGB2RGBA),mode='RGBA' )
        if self.mode == 'RGBA' and convert_type_str == 'RGB':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB),mode='RGB' )
        if self.mode == 'L' and convert_type_str == 'RGB':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB),mode='RGB' )
        if self.mode == 'L' and convert_type_str == 'RGBA':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGBA), mode='RGBA' )
        if self.mode == 'LA' and convert_type_str == 'RGBA':
            img = cv2.cvtColor(img_array[:,:,0],cv2.COLOR_GRAY2BGRA)
            img[:,:,3] = img_array[:,:,1]
            return ImageWrapper(img,mode='RGBA')
        if self.mode == 'LA' and convert_type_str == 'L':
            img = np.copy(img_array[:,:,0])
            img = img * img_array[:,:,1]
            return ImageWrapper(img,mode='L')
        if self.mode == 'RGB' and convert_type_str == 'L':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) )
        if self.mode == 'RGB' and convert_type_str == 'LUV':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_RGB2LUV))
        if self.mode == 'RGBA' and convert_type_str == 'L':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY) )
        max_value = np.iinfo(img_array.dtype).max
        if self.mode == 'RGBA' and convert_type_str == 'F':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY) /max_value)
        if self.mode == 'RGB' and convert_type_str == 'F':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)/max_value )
        if self.mode == 'L' and convert_type_str == 'F':
            return ImageWrapper(img_array/max_value)
        if self.mode == 'LA' and convert_type_str == 'F':
            img = np.copy(img_array[:, :, 0])
            img = img * img_array[:, :, 1]
            img = img.astype('float')
            return ImageWrapper(img/max_value,mode='F')
        return self

    def apply_alpha_to_mask(self, mask):
        """
        :param mask:
        :return:  The mask altered by the alpha channel of the given image
        @rtype : ImageWrapper
        """
        s = self.image_array.shape
        if self.mode.find('A') > 0 and len(s) > 3:
            img_array = np.asarray(mask)
            img_array = np.copy(img_array) if len(img_array.shape) == 2 else mask.to_mask().to_array()
            img_array[self.image_array[:, :, s[2]-1] == 0] = 255
            return ImageWrapper(img_array)
        return mask

    def to_mask(self):
        """
        white = selected, black = unselected
        @rtype : ImageWrapper
        """
        s = self.image_array.shape
        gray_image_temp = self.convert('L')
        if len(s) == 3 and self.mode.find('A') > 0 :
            gray_image = 255*np.ones(gray_image_temp.image_array.shape).astype('uint8')
            gray_image[self.image_array[:, :, self.image_array.shape[2]-1] == 0] = 0
        else:
            gray_image = np.ones(gray_image_temp.image_array.shape).astype('uint8') * 255
            gray_image[gray_image_temp.image_array == 0] = 0
        return ImageWrapper(gray_image)

    def to_16BitGray(self, equalize_colors=False):
        """
        Apply the alpha channel in the process of the conversion
        :param equalize_colors:
        :return: float image (mode = 'F')
        @rtype : ImageWrapper
        """
        s = self.image_array.shape
        if self.mode == 'F':
            return self
        if len(s) == 2:
            return ImageWrapper(tofloat(self.image_array))
        if self.mode == 'LA':
            return ImageWrapper(self.image_array[:, :, 0] * tofloat(self.image_array[:, :, 1]).astype('float32'))
        rgbaimg = self.convert('RGBA') if self.mode != 'RGBA' else self
        r, g, b = rgbaimg.image_array[:, :, 0], rgbaimg.image_array[:, :, 1], rgbaimg.image_array[:, :, 2]
        if equalize_colors:
            r = cv2.equalizeHist(r)
            g = cv2.equalizeHist(g)
            b = cv2.equalizeHist(b)
        a = tofloat(rgbaimg.image_array[:, :, 3]) if s[2] == 4 else np.ones((self.size[1], self.size[0]))
        gray = ((2.989 * r + 5.870 * g + 1.140 * b) * a)
        return ImageWrapper(gray.astype('uint16'))

    def to_float(self,equalize_colors=False):
        """
        Apply the alpha channel in the process of the conversion
        :param equalize_colors:
        :return: float image (mode = 'F')
        @rtype : ImageWrapper
        """
        s = self.image_array.shape
        if self.mode == 'F':
            return self
        if len(s) == 2:
            return ImageWrapper(tofloat(self.image_array))
        if self.mode == 'LA':
            return ImageWrapper(self.image_array[:,:,0] * tofloat(self.image_array[:, :, 1]).astype('float32'))
        rgbaimg  = self.convert('RGBA') if self.mode != 'RGBA' else self
        r, g, b = rgbaimg.image_array[:, :, 0], rgbaimg.image_array[:, :, 1], rgbaimg.image_array[:, :, 2]
        if equalize_colors:
            r = cv2.equalizeHist(r)
            g = cv2.equalizeHist(g)
            b = cv2.equalizeHist(b)
        a = tofloat(rgbaimg.image_array[:, :, 3]) if s[2] == 4 else np.ones((self.size[1],self.size[0]))
        gray = ((0.2989 * r + 0.5870 * g + 0.1140 * b) * a)
        return ImageWrapper(gray.astype('float32'))

    def resize(self,size, flag):
        if str(self.image_array.dtype) == 'uint8':
            return ImageWrapper(np.asarray(Image.fromarray(self.image_array).resize(size,flag)))
        return ImageWrapper(cv2.resize(self.image_array, size,fx=0.5, fy=0.5,interpolation = cv2.INTER_CUBIC))

    def invert(self):
        if str(self.image_array.dtype).startswith('f'):
            return ImageWrapper((1.0 - self.image_array).astype(self.image_array.dtype))
        return ImageWrapper((np.iinfo(self.image_array.dtype).max - self.image_array).astype(self.image_array.dtype))

    def apply_transparency(self):
        if self.mode.find('A') < 0:
            return self
        perc = tofloat(self.image_array[:, :, self.image_array.shape[2]-1])
        xx = np.copy(self.image_array)
        xx.flags['WRITEABLE'] = True
        for d in range(self.image_array.shape[2]-1):
            xx[:, :, d] = xx[:, :, d] * perc
        xx[:, :, self.image_array.shape[2]-1] = np.ones((xx.shape[0], xx.shape[1])) * float(np.iinfo(self.image_array.dtype).max)
        return ImageWrapper(xx)

    def overlay(self, image, color=[0,198,0]):
        """
        :param image:
        :return:new image with give n image overlayed
        @rtype : ImageWrapper
        """
        image_to_use = self.image_array if self.mode == 'RGA' else self.convert('RGB').image_array
        self_array = np.copy(image_to_use)
        if len(image_to_use.shape) != len(image.image_array.shape):
            image_array =  np.zeros(image_to_use.shape)
            image_array = image_array.astype('uint8')
            image_array[image.image_array<150,:] = color
            image_array[image.image_array >= 150, :] = [0, 0, 0]
        else:
            image_array = np.copy(np.asarray(image.image_array))
            image_array[np.all(image_array == [255,255,255],axis=2)] = [0,0,0]
        if image_array.dtype != self_array.dtype:
             image_array = image_array.astype(self_array.dtype)
             # for now, assume u16
             image_array*=256
        TUNE1 = 0.75
        TUNE2 = 0.75
        if (self_array.shape[0],self_array.shape[1]) != (image_array.shape[0],image_array.shape[1]):
            self_array = np.resize(self_array[:,:,0:3],image_array.shape)
        return ImageWrapper(cv2.addWeighted(image_array, TUNE1, self_array[:,:,0:3],  TUNE2,
                        0, self_array))

