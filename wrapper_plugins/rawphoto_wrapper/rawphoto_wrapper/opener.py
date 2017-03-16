
import numpy as np
from PIL import Image

def openRawFile(filename,isMask=None):
    from rawkit.raw import Raw
    raw_image = Raw(filename)
    buffered_image = np.array(raw_image.to_buffer())
    return (np.array(Image.frombytes('RGB', (raw_image.metadata.width, raw_image.metadata.height), buffered_image)),'RGB')
