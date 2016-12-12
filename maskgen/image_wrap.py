from PIL import Image
import cv2
import numpy as np
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

def openImageFile(filename,isMask=False):
   import os
   if not os.path.exists(filename):
       pos = filename.rfind('.')
       mod_filename = filename[0:pos] + filename[pos:].lower()
       if os.path.exists(mod_filename):
           filename = mod_filename
   if not os.path.exists(filename):
       raise ValueError("File not found: " + filename)
   try:
     with open(filename,'rb') as f:
          im = Image.open(filename)
          im.load()
          if im.format == 'TIFF' and filename.lower().find('tif') < 0:
            raw = openRaw(filename)
            if raw is not None and raw.size != im.size:
                return raw
          return ImageWrapper(np.asarray(im),mode=im.mode,info=im.info,to_mask =isMask)
   except:
      info = {}
      try:
          with TiffFile(filename) as tiffdata:
              for page in tiffdata:
                  for tag in page.tags.values():
                     t,v = tag.name, tag.value
                     if t.startswith('compress'):
                         info['compress'] = v
      except:
          pass
      try:
          return ImageWrapper( cv2.cvtColor(cv2.imread(filename, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGR2RGB),info=info,to_mask =isMask)
      except:
          return openRaw(filename)

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

    def save(self, filename, **kwargs):
        format = kwargs['format'] if 'format' in kwargs else 'PNG'
        format = 'TIFF' if self.image_array.dtype == 'uint16' else format
        newargs = dict(kwargs)
        newargs['format'] = format
        img_array = self.image_array
        if self.mode == 'F':
            img_array =  img_array * 256
            img_array = img_array.astype('uint8')
        if img_array.dtype == 'uint8' or self.mode == 'L':
            Image.fromarray(img_array).save(filename,**newargs)
            return
        newargs.pop('format')
        imsave(filename, self.image_array,**newargs)
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
          Produce a mask where all black areas are white
        @rtype : ImageWrapper
        """
        s = self.image_array.shape

        gray_image_temp = self.convert('L')
        gray_image = np.ones(gray_image_temp.image_array.shape).astype('uint8') * 255
        gray_image[gray_image_temp.image_array < np.iinfo(gray_image_temp.image_array.dtype).max] = 0
        if len(s) == 3 and self.mode.find('A') > 0 :
            gray_image[self.image_array[:, :, self.image_array.shape[2]-1] == 0] = 255
        return ImageWrapper(gray_image)

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

    def overlay(self, image):
        """
        :param image:
        :return:new image with give n image overlayed
        @rtype : ImageWrapper
        """
        image_to_use = self.image_array if len(self.image_array.shape) != 2 else self.convert('RGB').image_array
        self_array = np.copy(image_to_use)
        if len(image_to_use.shape) != len(image.image_array.shape):
            image_array =  np.ones(image_to_use.shape)*255
            image_array[image.image_array<150,:] = [0, 198, 0]
            image_array[image.image_array >= 150, :] = [0, 0, 0]
            image_array = image_array.astype('uint8')
        else:
            image_array =np.copy( np.asarray(image))
            image_array[np.all(image_array == [255,255,255],axis=2)] = [0,0,0]
        if image_array.dtype != self_array.dtype:
             image_array = image_array.astype(self_array.dtype)
             # for now, assume u16
             image_array*=256
        TUNE1 = 0.75
        TUNE2 = 0.75
        return ImageWrapper(cv2.addWeighted(image_array, TUNE1, self_array[:,:,0:3],  TUNE2,
                        0, self_array))

