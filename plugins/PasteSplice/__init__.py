from PIL import Image
import numpy as np
from sys import platform as sys_pf
import logging

if sys_pf == 'darwin':
    import matplotlib
    matplotlib.use("TkAgg")

import cv2
import random
import os
from maskgen.image_wrap import ImageWrapper, openImageFile
from maskgen import tool_set
from skimage import segmentation, color, measure, feature
from skimage.future import graph
import numpy as np
import math
from skimage.restoration import denoise_tv_bregman
from maskgen import cv2api


from matplotlib import transforms
from matplotlib.patches import Ellipse


class TransformedEllipse(Ellipse):
    def __init__(self, xy, width, height, angle=0.0, fix_x=1.0, **kwargs):
        Ellipse.__init__(self, xy, width, height, angle, **kwargs)

        self.fix_x = fix_x

    def _recompute_transform(self):
        center = (self.convert_xunits(self.center[0]),
                  self.convert_yunits(self.center[1]))
        width = self.convert_xunits(self.width)
        height = self.convert_yunits(self.height)
        self._patch_transform = transforms.Affine2D() \
            .scale(width * 0.5, height * 0.5) \
            .rotate_deg(self.angle) \
            .scale(self.fix_x, 1) \
            .translate(*center)


def minimum_bounding_box(image):
    # (contours, _) = cv2.findContours(image.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours, hierarchy = cv2api.findContours(image.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    selected = []
    for cnt in contours:
        try:
            M = cv2.moments(cnt)
            x = int(M['m10'] / M['m00'])
            y = int(M['m01'] / M['m00'])
            x1, y1, w, h = cv2.boundingRect(cnt)
            w = w - 1
            h = h - 1
            selected.append((w, h, w * h, x, y))
        except:
            continue

    selected = sorted(selected, key=lambda cnt: cnt[2], reverse=True)

    if len(selected) == 0:
        x, y, w, h = tool_set.widthandheight(image)
        selected = [(w, h, w * h, x + w / 2, y + h / 2)]
    return selected[0]


def minimum_bounding_ellipse_of_points(points):
    M = cv2.moments(points)
    x = int(M['m10'] / M['m00'])
    y = int(M['m01'] / M['m00'])
    if x < 0 or y < 0 or len(points) < 4:
        return None
    if len(points) == 4:
        (x1, y1), (MA, ma), angle = cv2.minAreaRect(points)
    else:
        (x1, y1), (MA, ma), angle = cv2.fitEllipse(points)
    return (x, y, MA, ma, angle, cv2.contourArea(points), points)


def minimum_bounding_ellipse(image):
    """
    :param image:
    :return:  (x, y, MA, ma, angle, area, contour)
    @rtype : (int,int,int,int,float, float,np.array)
    """
    (contours, _) = cv2api.findContours(image.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    selected = []
    for cnt in contours:
        try:
            bounded_info = minimum_bounding_ellipse_of_points(cnt)
            if bounded_info is not None:
                selected.append(bounded_info)
        except:
            continue
    if len(selected) == 0:
        return None
    selected = sorted(selected, key=lambda cnt: cnt[5], reverse=True)
    return selected[0] if len(selected) > 0 else None


def minimum_bounded_ellipse(image):
    image = feature.canny(image).astype(np.uint8) * 255
    coords = np.column_stack(np.nonzero(image))
    # find the embedded circle using random sample consensus
    try:
        model, inliers = measure.ransac(coords, measure.EllipseModel,
                                        min_samples=3, residual_threshold=1,
                                        max_trials=500)
    except Exception as ex:
        logging.getLogger('maskgen').error('minimum_bounded_ellipse {}'.fomat(str(ex)))
        raise ex
    return model.params


def build_transform_matrix(placement_ellipse, mask_ellipse):
    width_diff = placement_ellipse[2] - mask_ellipse[2]
    height_diff = placement_ellipse[3] - mask_ellipse[3]
    scale_factor = 1.0 + (float(width_diff) / mask_ellipse[2])
    height_scale = 1.0 + (float(height_diff) / mask_ellipse[3])
    scale_factor = height_scale if height_scale < scale_factor else scale_factor
    if scale_factor < 0.2 or scale_factor > 1.5:
        return None
    rotation_angle = mask_ellipse[4] - placement_ellipse[4]
    return cv2.getRotationMatrix2D((mask_ellipse[0], mask_ellipse[1]),
                                   rotation_angle, scale_factor)


def transform_image(image, transform_matrix):
    """
    :param image:
    :param transform_matrix:
    :return:
    @rtype array
    """
    return cv2.warpAffine(image, transform_matrix, (image.shape[1], image.shape[0]))


def build_random_transform(img_to_paste, mask_of_image_to_paste, image_center):
    scale = 0.5 + random.random()
    angle = 180.0 * random.random() - 90.0
    return cv2.getRotationMatrix2D(image_center, angle, scale)


def pasteAnywhere(img, img_to_paste, mask_of_image_to_paste, simple):
    # get gravity center for rotation
    w, h, area, cx_gra, cy_gra = minimum_bounding_box(mask_of_image_to_paste)

    if not simple:
        # use gravity center to rotate
        rot_mat = build_random_transform(img_to_paste, mask_of_image_to_paste, (cx_gra, cy_gra))
        img_to_paste = cv2.warpAffine(img_to_paste, rot_mat, (img_to_paste.shape[1], img_to_paste.shape[0]))
        mask_of_image_to_paste = cv2.warpAffine(mask_of_image_to_paste, rot_mat,
                                                (img_to_paste.shape[1], img_to_paste.shape[0]))
        # x,y is the Geometry center(gravity center), which can't align to the crop center(bounding box center)
        w, h, area, cx, cy = minimum_bounding_box(mask_of_image_to_paste)
    else:
        rot_mat = np.array([[1, 0, 0], [0, 1, 0]]).astype('float')

    # To calculate the bbox center
    x, y, w1, h1 = tool_set.widthandheight(mask_of_image_to_paste)

    if img.size[0] < w + 4:
        w = img.size[0] - 2
        xplacement = w / 2 + 1
    else:
        xplacement = random.randint(w / 2 + 1, img.size[0] - w / 2 - 1)

    if img.size[1] < h + 4:
        h = img.size[1] - 2
        yplacement = h / 2 + 1
    else:
        yplacement = random.randint(h / 2 + 1, img.size[1] - h / 2 - 1)

    output_matrix = np.eye(3, dtype=float)

    for i in range(2):
        for j in range(2):
            output_matrix[i, j] = rot_mat[i, j]

    # That is the correct offset
    output_matrix[0, 2] = rot_mat[0, 2] + xplacement - x - w1 / 2
    output_matrix[1, 2] = rot_mat[1, 2] + yplacement - y - h1 / 2

    return output_matrix, tool_set.place_in_image(
        ImageWrapper(img_to_paste).to_mask().to_array(),
        img_to_paste,
        np.asarray(img),
        (xplacement, yplacement),
        # x,y have no use
        rect=(x, y, w, h))

def performPaste(img,img_to_paste,approach,segment_algorithm):

    mask_of_image_to_paste = img_to_paste.to_mask().to_array()
    out2 = None
    if approach == 'texture':
        denoise_img = denoise_tv_bregman(np.asarray(img), weight=0.4)
        denoise_img = (denoise_img * 255).astype('uint8')
        gray = cv2.cvtColor(denoise_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        mask_of_image_to_paste_ellipse = minimum_bounding_ellipse(mask_of_image_to_paste)
        if mask_of_image_to_paste_ellipse is not None:
            img_to_paste = img_to_paste.apply_mask_rgba(mask_of_image_to_paste)
            dims = (math.ceil(denoise_img.shape[0] / 500.0) * 500.0, math.ceil(denoise_img.shape[1] / 500.0) * 500.0)
            sigma = max(1.0, math.log10(dims[0] * dims[1] / 10000.0) - 0.5)
            min_size = max(100.0, math.ceil(sigma * 10.0) * 10)
            while out2 is None and sigma < 5:
                if segment_algorithm == 'slic':
                    masksize = float(sum(sum(mask_of_image_to_paste)) / 255)
                    imgsize = float(img.size[0] * img.size[1])
                    labels1 = segmentation.slic(gray, compactness=5,
                                                n_segments=min(500, int(imgsize / (sigma * 2 * masksize))))
                else:
                    labels1 = segmentation.felzenszwalb(gray, scale=min_size, sigma=sigma, min_size=int(min_size))

                # Compute the Region Adjacency Graph using mean colors.

                #
                # Given an image and its initial segmentation, this method constructs the corresponding  RAG.
                # Each node represents a set of pixels  within image with the same label in labels.
                # The weight between two adjacent regions represents how similar or dissimilar two
                # regions are depending on the mode parameter.

                cutThresh = 0.000000005
                labelset = np.unique(labels1)
                while len(labels1) > 100000 or len(labelset) > 500:
                    g = graph.rag_mean_color(denoise_img, labels1, mode='similarity')
                    labels1 = graph.cut_threshold(labels1, g, cutThresh)
                    labelset = np.unique(labels1)
                    cutThresh += 0.00000001
                labelset = np.unique(labels1)
                for label in labelset:
                    if label == 0:
                        continue
                    mask = np.zeros(labels1.shape)
                    mask[labels1 == label] = 255
                    mask = mask.astype('uint8')
                    ret, thresh = cv2.threshold(mask, 127, 255, 0)
                    (contours, _) = cv2api.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                    areas = [(cnt, cv2.contourArea(cnt)) for cnt in contours
                             if cv2.moments(cnt)['m00'] > 2.0]
                    contours = sorted(areas, key=lambda cnt: cnt[1], reverse=True)
                    contours = contours[0: min(20, len(contours))]
                    if len(contours) > 0:
                        for contour in contours:
                            try:
                                placement_ellipse = minimum_bounding_ellipse_of_points(contour[0])
                                if placement_ellipse is not None:
                                    transform_matrix = build_transform_matrix(placement_ellipse,
                                                                              mask_of_image_to_paste_ellipse)
                                    if transform_matrix is None:
                                        continue
                                    transformed_image = transform_image(img_to_paste.to_array(), transform_matrix)
                                else:
                                    transformed_image = img_to_paste.to_array()
                                out2 = tool_set.place_in_image(
                                    ImageWrapper(transformed_image).to_mask().to_array(),
                                    transformed_image,
                                    np.asarray(img),
                                    (placement_ellipse[0], placement_ellipse[1]))
                                if out2 is not None:
                                    break
                            except Exception as e:
                                continue
                    if out2 is not None:
                        break
                sigma += 0.5

    if out2 is None:
        transform_matrix, out2 = pasteAnywhere(img, img_to_paste.to_array(), mask_of_image_to_paste,
                                               approach == 'simple')
    return transform_matrix,out2

def transform(img, source, target, **kwargs):
    img_to_paste = openImageFile(kwargs['donor'])
    pasteregionsize = kwargs['region size'] if 'region size' in kwargs else 1.0
    approach = kwargs['approach'] if 'approach' in kwargs else 'simple'
    segment_algorithm = kwargs['segment'] if 'segment' in kwargs else 'felzenszwalb'

    if pasteregionsize < 1.0:
        dims = (int(img.size[1]*pasteregionsize),int(img.size[0]*pasteregionsize))
    else:
        dims = (img.size[1],img.size[0])
    x = (img.size[1]-dims[0])/2
    y = (img.size[0]-dims[1])/2
    imgarray = np.asarray(img)
    if len(imgarray.shape) > 2:
        newimg = imgarray[x:dims[0]+x,y:dims[1]+y,:]
    else:
        newimg = imgarray[x:dims[0]+x, y:dims[1]+y]

    transform_matrix,out = performPaste(ImageWrapper(newimg),img_to_paste,approach,segment_algorithm)
    if pasteregionsize < 1.0:
        out2 = np.copy(imgarray)
        if len(imgarray.shape) > 2:
            out2[x:dims[0]+x, y:dims[1]+y, :] = out
        else:
            out2[x:dims[0]+x, y:dims[1]+y] = out
        out = out2
    ImageWrapper(out).save(target)
    return {'transform matrix': tool_set.serializeMatrix(
        transform_matrix)} if transform_matrix is not None else None, None


# the actual link name to be used.
# the category to be shown
def operation():
    return {'name': 'PasteSplice',
            'category': 'Paste',
            'description': 'Apply a mask to create an alpha channel',
            'software': 'OpenCV',
            'version': cv2.__version__,
            'arguments': {
                'donor': {
                    'type': 'donor',
                    'defaultvalue': None,
                    'description': 'Mask to set alpha channel to 0'
                },
                'approach': {
                    'type': 'list',
                    'values': ['texture', 'simple', 'random'],
                    'defaultvalue': 'random',
                    'description': "The approach to find the placement. Option 'random' includes random selection scale and rotation"
                },
                'segment': {
                    'type': 'list',
                    'values': ['felzenszwalb', 'slic'],
                    'defaultvalue': 'felzenszwalb',
                    'description': 'Segmentation algorithm for determiming paste region with simple set to no'
                },
                'region size': {
                    'type':'float[0:1]',
                    'default':1.0,
                    'description':'Paste region size from the center of image in percent 0 to 1. 1.0 is the entire image'
                }
            },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return None
