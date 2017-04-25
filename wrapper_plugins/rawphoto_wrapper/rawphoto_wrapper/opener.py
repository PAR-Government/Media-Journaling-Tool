
import numpy as np
from PIL import Image

def openRawFile(filename,isMask=None):
    from rawkit.raw import Raw
    with Raw(filename=filename) as raw_image:
        buffered_image = np.array(raw_image.to_buffer())
        return (np.array(Image.frombytes('RGB',
                                         (raw_image.metadata.height, raw_image.metadata.width), buffered_image)),'RGB')
