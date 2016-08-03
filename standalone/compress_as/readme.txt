compress_as.py will save an image using the jpg quantization tables of a specified jpeg image.

argument format:
python compress_as.py <source_image> <target_image>

source_image should be a .jpg image.
target_image can be whatever image formats are supported by the python imaging library
(Pillow - http://pillow.readthedocs.io/en/3.2.x/handbook/image-file-formats.html)

dependencies:
pillow (pip)
bitstring (pip)