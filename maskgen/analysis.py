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
        A1 = (A1 - min(A1))/(max(A1) - min(A1)) * 255
    PCI = np.reshape(A1, i.image_array[:, :, 0].shape).astype('uint8')
    if normalize:
        PCI = cv2.equalizeHist(PCI)
    return ImageWrapper(PCI)

def ela(i):
    from PIL import Image
    import time
    import os
    tmp = 't' + str(time.clock()) + '.jpg'
    Image.fromarray(i.image_array).save(tmp,'JPEG', quality=95)
    with open(tmp,'r') as f:
        i_qa = Image.open(f)
        i_qa_array = np.asarray(i_qa)
        i_qa.load()
    os.remove(tmp)
    ela_im = i.image_array - i_qa_array
    maxdiff = np.max(ela_im)
    mindiff = np.min(ela_im)
    scale = 255.0 / (maxdiff - mindiff)
    ela_im = (ela_im - mindiff) * scale
    return ImageWrapper(ela_im.astype('uint8'))