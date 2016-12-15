from PIL import Image
import numpy as np
import cv2
import random
import os
from maskgen.image_wrap import ImageWrapper
from maskgen import tool_set,image_wrap
from skimage import  segmentation, color,measure,feature
from skimage.future import graph
import numpy as np
from scipy.spatial import ConvexHull
import math
from skimage.restoration import denoise_tv_bregman

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
    (contours, _) = cv2.findContours(image.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    selected = []
    for cnt in contours:
        try:
            x, y, w, h = cv2.boundingRect(cnt)
            selected.append((w,h,w*h,x,y))
        except:
            continue
    selected = sorted(selected, key=lambda cnt: cnt[2], reverse=True)
    return selected[0] if len(selected) > 0 else None

def minimum_bounding_ellipse(image):
    """
    :param image:
    :return:  (x, y, MA, ma, angle, area, contour)
    @rtype : (int,int,int,int,float, float,np.array)
    """
    (contours, _) = cv2.findContours(image.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    selected = []
    for cnt in contours:
        try:
            M = cv2.moments(cnt)
            x = int(M['m10'] / M['m00'])
            y = int(M['m01'] / M['m00'])
            if x < 0 or y < 0 or len(cnt) < 5:
                continue
            (x1, y1), (MA, ma), angle = cv2.fitEllipse(cnt)
            selected.append((x,y,MA,ma, angle,cv2.contourArea(cnt), cnt))
        except:
            continue
    if len(selected) == 0:
        return None
    selected = sorted(selected, key=lambda cnt: cnt[5], reverse=True)
    return selected[0] if len(selected) > 0 else None

def minimum_bounded_ellipse(image):
    image = feature.canny(image).astype(np.uint8)*255
    coords = np.column_stack(np.nonzero(image))
    # find the embedded circle using random sample consensus
    try:
       model, inliers = measure.ransac(coords, measure.EllipseModel,
                                    min_samples=3, residual_threshold=1,
                                    max_trials=500)
    except Exception as ex:
       print ex
       raise ex
    return model.params

def build_transform_matrix(placement_ellipse,mask_ellipse):
    width_diff = placement_ellipse[2]-mask_ellipse[2]
    height_diff = placement_ellipse[3] - mask_ellipse[3]
    scale_factor = 1.0 + (float(width_diff)/mask_ellipse[2])
    height_scale = 1.0 + (float(height_diff)/mask_ellipse[3])
    scale_factor = height_scale if height_scale < scale_factor else scale_factor
    if scale_factor < 0.2 or scale_factor > 1.5:
        return None
    rotation_angle = mask_ellipse[4]-placement_ellipse[4]
    return cv2.getRotationMatrix2D((mask_ellipse[0],mask_ellipse[1]),
                                   rotation_angle,scale_factor)

def transform_image(image,transform_matrix):
    """
    :param image:
    :param transform_matrix:
    :return:
    @rtype array
    """
    return cv2.warpAffine(image,transform_matrix,(image.shape[0],image.shape[1]))

def widthandheight(img):
    a = np.where(img != 0)
    bbox = np.min(a[0]), np.max(a[0]), np.min(a[1]), np.max(a[1])
    w,h = bbox[1] - bbox[0], bbox[3] - bbox[2]
    return bbox[0]+w/2,bbox[2]+h/2,w,h

def place_in_image(mask,image_to_place,image_to_cover, placement_center):
    x,y,w, h = widthandheight(mask)
    w += w%2
    h += h%2
    x_offset = int(placement_center[0]) - int(math.floor(w/2))
    y_offset = int(placement_center[1]) - int(math.floor(h/2))
    mask_x_offset = int(x) - int(math.floor(w / 2))
    mask_y_offset = int(y) - int(math.floor(h / 2))
    if mask_y_offset<0:
        return None
    if mask_x_offset<0:
        return None
    if y_offset < 0:
        return None
    if x_offset < 0:
        return None
    if w < 25 or h < 25:
        return None
    image_to_cover = np.copy(image_to_cover)
    flipped_mask = 255 - mask
    for c in range(0, 3):
        image_to_cover[x_offset:x_offset + w,y_offset:y_offset + h,  c] = \
        image_to_cover[ x_offset:x_offset + w,y_offset:y_offset + h, c] * \
        (flipped_mask[mask_x_offset:mask_x_offset+w,mask_y_offset:mask_y_offset+h]/255) + \
        image_to_place[mask_x_offset:mask_x_offset + w,mask_y_offset:mask_y_offset + h, c] * \
        (mask[mask_x_offset:mask_x_offset + w,mask_y_offset:mask_y_offset + h]/255)
    return image_to_cover

def minimum_bounding_rectangle(image):
    """
    Find the smallest bounding rectangle for a set of points.
    Returns a set of points representing the corners of the bounding box.

    :param points: an nx2 matrix of coordinates
    :rval: an nx2 matrix of coordinates
    """
    from scipy.ndimage.interpolation import rotate

    im2, contours, hierarchy = cv2.findContours(image.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    points = contours[0]

    pi2 = np.pi/2.0

    # get the convex hull for the points
    hull_points = points[ConvexHull(points).vertices]

    # calculate edge angles
    edges = np.zeros((len(hull_points)-1, 2))
    edges = hull_points[1:] - hull_points[:-1]

    angles = np.zeros((len(edges)))
    angles = np.arctan2(edges[:, 1], edges[:, 0])

    angles = np.abs(np.mod(angles, pi2))
    angles = np.unique(angles)

    # find rotation matrices
    # XXX both work
    rotations = np.vstack([
        np.cos(angles),
        np.cos(angles-pi2),
        np.cos(angles+pi2),
        np.cos(angles)]).T
#     rotations = np.vstack([
#         np.cos(angles),
#         -np.sin(angles),
#         np.sin(angles),
#         np.cos(angles)]).T
    rotations = rotations.reshape((-1, 2, 2))

    # apply rotations to the hull
    rot_points = np.dot(rotations, hull_points.T)

    # find the bounding points
    min_x = np.nanmin(rot_points[:, 0], axis=1)
    max_x = np.nanmax(rot_points[:, 0], axis=1)
    min_y = np.nanmin(rot_points[:, 1], axis=1)
    max_y = np.nanmax(rot_points[:, 1], axis=1)

    # find the box with the best area
    areas = (max_x - min_x) * (max_y - min_y)
    best_idx = np.argmin(areas)

    # return the best box
    x1 = max_x[best_idx]
    x2 = min_x[best_idx]
    y1 = max_y[best_idx]
    y2 = min_y[best_idx]
    r = rotations[best_idx]

    rval = np.zeros((4, 2))
    rval[0] = np.dot([x1, y2], r)
    rval[1] = np.dot([x2, y2], r)
    rval[2] = np.dot([x2, y1], r)
    rval[3] = np.dot([x1, y1], r)

    return rval

def pasteAnywhere(img, img_to_paste,mask_of_image_to_paste,mask_of_image_to_paste_ellipse):
    w,h,area,x,y = minimum_bounding_box(mask_of_image_to_paste)
    xplacement = random.randint(w/2+1, img.size[1]-w/2-1)
    yplacement = random.randint(h/2+1,img.size[0]-h/2-1)
    return place_in_image(
                          ImageWrapper(img_to_paste).to_mask().invert().to_array(),
                          img_to_paste,
                          np.asarray(img),
                          (xplacement, yplacement))

def transform(img,source,target,**kwargs):
    img_to_paste =kwargs['donor'][0]
    mask_of_image_to_paste = img_to_paste.to_mask().invert().to_array()
    denoise_img = denoise_tv_bregman(np.asarray(img), weight=0.4)
    denoise_img = (denoise_img * 255).astype('uint8')
    gray = cv2.cvtColor(denoise_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    mask_of_image_to_paste_ellipse = minimum_bounding_ellipse(mask_of_image_to_paste)
    img_to_paste = img_to_paste.apply_mask_rgba(mask_of_image_to_paste)
    out2 = None
    sigma = 1
    while out2 is None and sigma<5:
        #labels1 = sgmentation.slic(gray, compactness=0.5, n_segments=200)e
        labels1= segmentation.felzenszwalb(denoise_img, scale=100, sigma=sigma, min_size=100)

        #Compute the Region Adjacency Graph using mean colors.
        #
        # Given an image and its initial segmentation, this method constructs the corresponding  RAG.
        # Each node represents a set of pixels  within image with the same label in labels.
        # The weight between two adjacent regions represents how similar or dissimilar two
        # regions are depending on the mode parameter.
        #g = graph.rag_mean_color(gray, labels1, mode='similarity')
        #out2 = color.label2rgb(labels1, gray, kind='avg')
        labelset = np.unique(labels1)
        for label in labelset:
            if label == 0:
                continue
            mask  = np.zeros(labels1.shape)
            mask[labels1==label] = 255
            mask = mask.astype('uint8')
            ret, thresh = cv2.threshold(mask, 127, 255, 0)
            (contours, _) = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            if len(contours) > 0:
                for cnt in contours:
                    try:
                        mask = np.zeros(labels1.shape)
                        cv2.fillConvexPoly(mask,cnt,255)
                        placement_ellipse = minimum_bounding_ellipse(mask.astype('uint8'))
                        if placement_ellipse is None:
                           continue
                        transform_matrix = build_transform_matrix(placement_ellipse,mask_of_image_to_paste_ellipse)
                        if transform_matrix is None:
                            continue
                        transformed_image = transform_image(img_to_paste.to_array(), transform_matrix)
                        #ImageWrapper(transformed_image).save('s.png')
                        #img_to_paste.save('i.png')
                        out2 = place_in_image(
                                              ImageWrapper(transformed_image).to_mask().invert().to_array(),
                                              transformed_image,
                                              np.asarray(img),
                                              (placement_ellipse[0], placement_ellipse[1]))
                        if out2 is not None:
                            break
                    except Exception as e:
                        #print e
                        continue
            if out2 is not None:
                break
        sigma+=1
    if out2 is None:
        out2 = pasteAnywhere(img, img_to_paste.to_array(),mask_of_image_to_paste,mask_of_image_to_paste_ellipse)
    ImageWrapper(out2).save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return {'name':'PasteSplice',
          'category':'Paste',
          'description':'Apply a mask to create an alpha channel',
          'software':'OpenCV',
          'version':'2.4.13',
          'arguments':{
              'donor':{
                  'type':'donor',
                  'defaultvalue':None,
                  'description':'Mask to set alpha channel to 0'
              }
          },
          'transitions': [
              'image.image'
          ]
  }


# def args():
#   return [('donor',None,'Mask to set alpha channel to 0')]

def suffix():
    return None