import numpy as np
import cv2

"""
Following source code and articles from:
Ana B. Petro, Catalina Sbert and Jean-Michel Moral, Multiscale Retinex, Image Processing On Line, 2014 pp. 71-88
https://doi.org/10.5021/ipol.2014.107
"""


def singleScaleRetinex(img, sigma):
    # mean of the image at different spatial resolutions by applying Gaussian filters of different sizes
    retinex = np.log(img) - np.log(cv2.GaussianBlur(img, (0, 0), sigma))
    return np.nan_to_num(retinex)


def multiScaleRetinex(img, sigma_list):
    # average over single retinex applied for each sigma
    retinex = np.zeros_like(img)
    for sigma in sigma_list:
        retinex += singleScaleRetinex(img, sigma)
    retinex = retinex / len(sigma_list)
    return retinex


def colorRestoration(img, retinex, alpha, beta):
    # the multi scale image result with the original image in order to restore
    # the information about intensity differences between the different
    # regions of the picture
    img_sum = np.sum(img, axis=2, keepdims=True)
    # public debate...which one
    # return beta * (np.log(alpha * img * retinex) - np.log(img_sum))
    return retinex * (beta * (np.log(alpha * img) - np.log(img_sum)))


def simplestColorBalance(img, low_clip, high_clip):
    # Limare1 et al. Simple Color Balance
    # Image Processing Online
    # ISSN 2105-1232 2011 IPOL
    img_c = np.copy(img).astype('float')
    image_size = img.shape[0] * img.shape[1]
    for i in range(img.shape[2]):
        sortdata = sorted(img.flatten())
        per1 = (int)(low_clip * image_size);
        minval = sortdata[per1];
        per2 = (int)(high_clip * image_size);
        maxval = sortdata[per2];
        scale = 255.0 / (maxval - minval)
        maxpositions = img[:, :, i] > maxval
        minpositions = img[:, :, i] < minval
        img_c[:, :, i] = scale * (img[:, :, i] - minval)
        img_c[minpositions, i] = 0.0
        img_c[maxpositions, i] = 255.0
    return img_c


def gain_offset(img, G=30, b=-6):
    return np.uint8(np.minimum(np.maximum(G * (img - b), 0), 255))

class MultiScaleResinex:
    """
    MSRCR
    """

    def __init__(self, sigma_list, G=30, b=-6, alpha=125.0, beta=46.0,
                 colorBalance=None):
        self.sigma_list = sigma_list
        self.b = b
        self.alpha = alpha
        self.beta = beta
        self.G = G
        self.colorBalance = colorBalance

    def __call__(self, img):
        img = np.float64(img)
        img_retinex = multiScaleRetinex(img, self.sigma_list)
        img_color = colorRestoration(img, img_retinex, self.alpha, self.beta)
        if self.colorBalance is None:
            img_msrcr = gain_offset(img_color, G=self.G, b=self.b)
        else:
            img_msrcr = simplestColorBalance(img_color, self.colorBalance[0], self.colorBalance[1])
        return img_msrcr.astype('uint8')


class MultiScaleResinexLab(MultiScaleResinex):
    """
    MSRCR Use the LAB Color Space
    """
    def __init__(self,
                 sigma_list,
                 G=30,
                 b=-6,
                 alpha=125.0,
                 beta=46.0,
                 colorBalance=None):
        MultiScaleResinex.__init__(self,
                                   sigma_list=sigma_list,
                                   G=G,
                                   b=b,
                                   alpha=alpha,
                                   beta=beta,
                                   colorBalance=colorBalance)

    def __call__(self, img):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        intensity = np.float64(lab[:, :, 0]) + 0.001
        intensity_r = multiScaleRetinex(intensity, self.sigma_list)
        intensity_r = np.expand_dims(intensity_r, 2)
        if self.colorBalance is None:
            img_msrcr = gain_offset(intensity_r, G=self.G, b=self.b)
        else:
            img_msrcr = simplestColorBalance(intensity_r, self.colorBalance[0], self.colorBalance[1])
        #print img_msrcr
        lab[:, :, 0] = img_msrcr[:, :, 0]
        gbr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        return gbr


class MultiScaleResinexChromaPerservation(MultiScaleResinex):
    """
    MSRCP
    """

    def __init__(self,
                 sigma_list,
                 G=30,
                 b=-6,
                 alpha=125.0,
                 beta=46.0,
                 colorBalance=None):
        MultiScaleResinex.__init__(self, sigma_list=sigma_list, G=G, b=b, alpha=alpha, beta=beta,
                                   colorBalance=colorBalance)

    def __call__(self, img):
        img = np.float64(img) + 0.001

        intensity = np.sum(img, axis=2) / img.shape[2]

        retinex = multiScaleRetinex(intensity, self.sigma_list)

        intensity = np.expand_dims(intensity, 2)

        retinex = np.expand_dims(retinex, 2)

        intensity_single = simplestColorBalance(retinex, self.colorBalance[0], self.colorBalance[1])

        intensity_single = (intensity_single - np.min(intensity_single)) / \
                           (np.max(intensity_single) - np.min(intensity_single)) * \
                           255.0 + 1.0

        img_msrcp = np.zeros_like(img)

        max_channel = np.max(img, axis=2)
        min_intensity = np.minimum(256.0 / max_channel, intensity_single[:, :, 0] / intensity[:, :, 0])
        img_msrcp[:, :, 0] = min_intensity * img[:, :, 0]
        img_msrcp[:, :, 1] = min_intensity * img[:, :, 1]
        img_msrcp[:, :, 2] = min_intensity * img[:, :, 2]

        return np.uint8(img_msrcp - 0.001)
