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


def openImageFile(filename,isMask=False):
   import os
   if not os.path.exists(filename):
       pos = filename.rfind('.')
       mod_filename = filename[0:pos] + filename[pos:].lower()
       if os.path.exists(mod_filename):
           filename = mod_filename
   try:
     with open(filename,'rb') as f:
          im = Image.open(filename)
          im.load()
          return ImageWrapper(np.asarray(im),info=im.info,to_mask =isMask)
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
          import rawpy
          with rawpy.imread(filename) as raw:
              return ImageWrapper(raw.postprocess(),to_mask =isMask)


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
    else:
        return 'RGB'

class ImageWrapper:
    def __init__(self,image_array, to_mask=False,info=None):
        if str(type(image_array)) == 'ImageWrapper':
            self.image_array = image_array.image_array
        else:
            self.image_array = image_array
        self.info = info
        self.mode = get_mode(image_array)
        self.size = (image_array.shape[1],image_array.shape[0])
        if to_mask and self.mode != 'L':
            self.image_array = cv2.cvtColor(self.to_rgb(type='uint8').image_array,cv2.COLOR_RGBA2GRAY)
            self.mode = 'L'

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

    def to_rgb(self, type=None):
        type = self.image_array.dtype if type is None else type
        s = self.image_array.shape
        if (len(s)) > 2 and s[2] > 3:
            alpha = self.image_array[:,:,3]
            zeros = np.zeros((self.size[1],self.size[0]))
            zeros[alpha > 0] = 1
            img_array2 = np.zeros((self.image_array.shape[0],self.image_array.shape[1],3))
            for i in range(3):
                img_array2[:, :, i] = self.image_array[:, :, i] * zeros
            img_array2 = img_array2.astype(self.image_array.dtype)
            return ImageWrapper(totype(img_array2,type))
        elif len(s) == 2:
             return ImageWrapper(cv2.cvtColor(totype(self.image_array,type),cv2.COLOR_GRAY2RGB))
        return ImageWrapper(totype(np.copy(self.image_array),type))

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
            return ImageWrapper(np.asarray(Image.fromarray(img_array).convert(convert_type_str)))
        if self.mode == 'RGB' and convert_type_str == 'RGBA':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_RGB2RGBA) )
        if self.mode == 'RGBA' and convert_type_str == 'RGB':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB) )
        if self.mode == 'L' and convert_type_str == 'RGB':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB) )
        if self.mode == 'L' and convert_type_str == 'RGBA':
            return ImageWrapper(cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGBA) )
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
        return self

    def apply_alpha_to_mask(self, image):
        s = self.image_array.shape
        if len(s) == 3 and self.image_array.shape[2] == 4:
            img_array = np.asarray(image)
            img_array = np.copy(img_array) if len(img_array.shape) == 2 else image.to_mask().to_array()
            img_array[self.image_array[:, :, 3] == 0] = 255
            return ImageWrapper(img_array)
        return image

    def to_mask(self):
        """
          Produce a mask where all black areas are white
        """
        s = self.image_array.shape

        gray_image_temp = self.convert('L')
        gray_image = np.ones(gray_image_temp.image_array.shape).astype('uint8') * 255
        gray_image[gray_image_temp.image_array < np.iinfo(gray_image_temp.image_array.dtype).max] = 0
        if len(s) == 3 and self.image_array.shape[2] == 4:
            gray_image[self.image_array[:, :, 3] == 0] = 255
        return ImageWrapper(gray_image)

    def to_float(self,equalize_colors=False):
        s = self.image_array.shape
        if len(s) == 2:
            return ImageWrapper(tofloat(self.image_array))
        if str(self.image_array.dtype) == 'uint8':
            img = np.asarray(Image.fromarray(self.image_array).convert('F'))
        r, g, b = self.image_array[:, :, 0], self.image_array[:, :, 1], self.image_array[:, :, 2]
        if equalize_colors:
            r = cv2.equalizeHist(r)
            g = cv2.equalizeHist(g)
            b = cv2.equalizeHist(b)
        a = tofloat(self.image_array[:, :, 3]) if s[2] == 4 else np.ones((self.size[1],self.size[0]))
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
        perc = tofloat(self.image_array[:, :, 3])
        xx = np.copy(self.image_array)
        xx.flags['WRITEABLE'] = True
        for d in range(3):
            xx[:, :, d] = xx[:, :, d] * perc
        xx[:, :, 3] = np.ones((xx.shape[0], xx.shape[1])) * float(np.iinfo(self.image_array.dtype).max)
        return ImageWrapper(xx)

