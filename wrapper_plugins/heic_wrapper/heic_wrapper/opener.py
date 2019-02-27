def open_heic(filename, isMask=False):
    from wand.image import Image as WandImage
    from PIL import Image
    import numpy as np
    from io import BytesIO
    from maskgen.image_wrap import ImageWrapper
    depthmap = {'8': 'uint8', '16':'uint16', '32':'uint32'}
    with WandImage(filename=filename) as wand_img:
       with wand_img.convert(format='bmp') as img:
           img_buffer = np.asarray(bytearray(img.make_blob()), dtype=depthmap[str(img.depth)])
           bytesio = BytesIO(img_buffer)
           pilImage = Image.open(fp=bytesio)
           return ImageWrapper(np.asarray(pilImage), mode=pilImage.mode, info=pilImage.info, to_mask=isMask, filename=filename)