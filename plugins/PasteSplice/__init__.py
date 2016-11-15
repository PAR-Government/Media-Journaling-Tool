from PIL import Image
import numpy as np
import cv2
import random
from maskgen.image_wrap import ImageWrapper
from maskgen import tool_set,image_wrap
from skimage import  segmentation, color,measure
from skimage.future import graph
import numpy as np
from scipy.spatial import ConvexHull

def minimum_bounding_rectangle(image):
    """
    Find the smallest bounding rectangle for a set of points.
    Returns a set of points representing the corners of the bounding box.

    :param points: an nx2 matrix of coordinates
    :rval: an nx2 matrix of coordinates
    """
    from scipy.ndimage.interpolation import rotate

    im2, contours, hierarchy = cv2.findContours(image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    points = contours[0]

    pi2 = np.pi/2.

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


def transform(img,source,target,**kwargs):
    img_to_paste = tool_set.openImageFile(kwargs['inputimagename'])
    mask_of_image = img_to_paste.to_mask().invert()
    gray = np.asarray( img.convert('L')).astype('uint8')
    labels1 = segmentation.slic(gray, compactness=0.1, n_segments=400)
    g = graph.rag_mean_color(gray, labels1, mode='similarity')
    labels2 = graph.cut_normalized(labels1, g)
    out2 = color.label2rgb(labels2, gray, kind='avg')
    bins = np.histogram(out2,bins=256)[0]
    maxbin = max(bins)
    label = np.where(np.asarray(bins) == maxbin)[0][0]
    mask  = np.zeros(out2.shape)
    mask[out2==label] = 255
    coords = np.column_stack(np.nonzero(mask))
    model, inliers = measure.ransac(coords, measure.CircleModel,
                                    min_samples=3, residual_threshold=1,
                                    max_trials=500)
    width = model.params[2]*2
    rec = minimum_bounding_rectangle(mask_of_image)
    ImageWrapper(out2).save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['PasteSplice','Paste','Apply a mask to create an alpha channel','OpenCV','2.4.13']

def args():
  return [('inputimagename',None,'Mask to set alpha channel to 0')]

def suffix():
    return None