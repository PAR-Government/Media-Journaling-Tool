# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import numpy as np
from maskgen.image_wrap import  ImageWrapper

def pca(i,component=0, normalize=False):
    from sklearn.decomposition import PCA
    import cv2
    i1 = np.reshape(i.image_array[:,:,0],i.size[1]*i.size[0])
    i2 = np.reshape(i.image_array[:,:,1],i.size[1]*i.size[0])
    i3 = np.reshape(i.image_array[:,:,2],i.size[1]*i.size[0])
    X= np.stack([i1,i2,i3])
    pca = PCA(3)
    pca.fit_transform(X)
    A = pca.components_[component] * pca.explained_variance_ratio_[component]
    A1 = (A - min(A)) / (max(A) - min(A)) * 255
    if normalize:
        imhist, bins = np.histogram(A1, 256, normed=True)
        cdf = imhist.cumsum()  # cumulative distribution function
        cdf = 255 * cdf / cdf[-1]
        A1 = np.interp(A1, bins[:-1], cdf)
    PCI = np.reshape(A1, i.image_array[:, :, 0].shape).astype('uint8')
    return ImageWrapper(PCI)

def histeq(im,nbr_bins=256):
   #get image histogram
   imhist,bins = np.histogram(im.flatten(),nbr_bins,normed=True)
   cdf = imhist.cumsum() #cumulative distribution function
   cdf = 255 * cdf / cdf[-1] #normalize
   #use linear interpolation of cdf to find new pixel values
   im2 = np.interp(im.flatten(),bins[:-1],cdf)
   return im2.reshape(im.shape)

def ela(i):
    from PIL import Image
    import time
    import os
    tmp = 't' + str(time.clock()) + '.jpg'
    Image.fromarray(i.image_array).save(tmp,'JPEG', quality=95)
    with open(tmp,'rb') as f:
        i_qa = Image.open(f)
        i_qa_array = np.asarray(i_qa)
        i_qa.load()
    os.remove(tmp)
    ela_im = i.image_array - i_qa_array
    maxdiff = np.max(ela_im)
    mindiff = np.min(ela_im)
    scale = 255.0 / (maxdiff - mindiff)
    for channel in range(ela_im.shape[2]):
        ela_im[:,:,channel] = histeq(ela_im[:,:,channel]) # - mindiff) * scale
    return ImageWrapper(ela_im.astype('uint8'))