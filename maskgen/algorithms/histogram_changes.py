# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
from math import log
import numpy as np


def packImgBits(img, bits_to_use=16):
    """
    :param img:
    :param bits:
    :return:
    @type img: numpy.ndarray
    @type bits: int
    """
    shift_bits = img.dtype.itemsize * 8 - bits_to_use
    max_image = np.max(img)
    hist, bin_edges = np.histogram(img, bins=range(max_image + 2), )
    # shift the image histogram to the left to remove unused bins
    # find the second histogram bin that has more than 10 values
    # and subtract it from every pixel value
    adjustment_amount = np.argwhere(hist > 10)[1][0]
    img = np.clip(img.astype('int64') - adjustment_amount, 0, max_image).astype(img.dtype)
    # drop the <bits> number of LSBs
    img = np.right_shift(img, shift_bits)
    return img

def get_gauss_kernel(size=3,sigma=1):
    center=(int)(size/2)
    kernel=np.zeros((size,size))
    for i in range(size):
       for j in range(size):
          diff=np.sqrt((i-center)**2+(j-center)**2)
          kernel[i,j]=np.exp(-(diff**2)/(2*sigma**2))
    return kernel/np.sum(kernel)

def packImgBitsFFT(img, max_bits=5):
    """
    :param img:
    :param bits:
    :return:
    @type img: numpy.ndarray
    @type bits: int
    """
    from scipy import fftpack, signal
    amount =  (1<<16) if img.dtype == np.uint16 else (1<<8)
    img_output = img.copy()
    kernel = get_gauss_kernel(21,1)
    #freq_kernel = fftpack.fft2(fftpack.ifftshift(kernel))
    for c in range( img.shape[2]):
        im_fft = np.fft.fft2(img[:,:,c])
        convolved = signal.convolve2d(im_fft.real, kernel)
        im_blur = fftpack.ifft2(convolved).real
        diff_x = (im_blur.shape[0] - img_output.shape[0])/2
        diff_y = (im_blur.shape[1] - img_output.shape[1])/2
        img_output[:,:,c] = (amount * im_blur / np.max(im_blur))[diff_x:-diff_x,diff_y:-diff_y]
    return img_output


def packImgBitsS(img, max_bits=5):
    """
    :param img:
    :param bits:
    :return:
    @type img: numpy.ndarray
    @type bits: int
    """
    from scipy import fftpack, signal
    amount =  (1<<16) if img.dtype == np.uint16 else (1<<8)

    t = np.linspace(-10, 10, 30)
    bump = np.exp(-0.1 * t ** 2)
    bump /= np.trapz(bump)  # normalize the integral to 1
    # make a 2-D kernel out of it
    kernel = bump[:, np.newaxis] * bump[np.newaxis, :]
    kernel_ft = fftpack.fft2(kernel, shape=img.shape[:2], axes=(0, 1))
    # convolve
    img_ft = fftpack.fft2(img, axes=(0, 1))
    # the 'newaxis' is to match to color direction
    img2_ft = kernel_ft[:, :, np.newaxis] * img_ft
    img2 = fftpack.ifft2(img2_ft, axes=(0, 1)).real
    img_output = img2.copy()
    return img_output