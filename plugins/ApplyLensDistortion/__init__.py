# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from PIL import Image
import numpy as np
import cv2
import math
from maskgen import tool_set
from maskgen.cv2api import cv2api_delegate
"""
   References
   --------------
   [1] http://en.wikipedia.org/wiki/Distortion_(optics), August 2012.

   [2] Harri Ojanen, "Automatic Correction of Lens Distortion by Using
       Digital Image Processing," July 10, 1999.

   [3] G.Vassy and T.Perlaki, "Applying and removing lens distortion in post
       production," year???

   [4] http://www.mathworks.com/products/demos/image/...
       create_gallery/tform.html#34594, August 2012.

   Adapted from a Matlab implementation by Jaap de Vries, 8/31/2012"
"""

def cart2pol(x, y):
    rho = np.sqrt(x ** 2 + y ** 2)
    phi = np.arctan2(y, x)
    return (rho, phi)


def pol2cart(rho, phi):
    x = rho * np.cos(phi)
    y = rho * np.sin(phi)
    return (x, y)


def _lens_distort(input_array, k, bordertype='fit', interpolation='linear', padmethod='symmetric', model=None):
    output = np.zeros(input_array.shape)

    interp_map = {'linear':cv2api_delegate.inter_linear,
                  'cubic':cv2api_delegate.inter_cubic,
                  'nearest':cv2api_delegate.inter_nn}
    border_map={'symmetric':cv2.BORDER_REFLECT,
                'fill': cv2.BORDER_CONSTANT,
                'replicate': cv2.BORDER_REPLICATE,
                'bound': cv2.BORDER_CONSTANT,
                'circular': cv2.BORDER_WRAP
                }
    def _correct_distortion(I, K, bordertype='fit',model=None):
        M = I.shape[0]  # (y rows)
        N = I.shape[1]  # (x)
        center = int(round(float(N) / 2.0)), int(round(float(M) / 2.0))
        xi, yi = np.meshgrid(range(N), range(M))
        #xi = xi + 1  Matlab is from 1 to N, Python is from 0 to N-1
        #yi = yi + 1
        xt = xi.reshape(xi.shape[0] * xi.shape[1], order='F') - center[0]
        yt = yi.reshape(yi.shape[0] * yi.shape[1], order='F') - center[1]
        r, theta = cart2pol(xt, yt)
        # calculate the maximum vector( image center to image corner) to be used
        # for normalization
        R = math.sqrt(center[0] ** 2 + center[1] ** 2)
        # Normalize the polar coordinate r to range between 0 and 1
        r = r / R
        # Apply the r-based transformation
        s = model(r, k)
        # Denormalize s
        s2 = s * R
        # Find a scaling parameter based on selected border type
        brcor = _correct_border(r, s, k, center, R, bordertype=bordertype)
        s2 = s2 * brcor
        # Convert back to cartesians
        ut, vt = pol2cart(s2, theta)
        u = ut.reshape(xi.shape, order='F') + center[0]
        v = vt.reshape(yi.shape, order='F') + center[1]

        #tmap_B = np.concatenate((u[..., np.newaxis], v[..., np.newaxis]), axis=-1)
        return cv2.remap(I, u.astype(np.float32), v.astype(np.float32),
                         interp_map[interpolation],
                         borderMode=border_map[padmethod], borderValue=255)

    def _correct_border(r, s, k, center, R, bordertype='fit'):
        mincenter = min(center) / R
        if k < 0:
            if bordertype == 'fit':
                return r[0] / s[0]
            else:
                return 1 / (1 + k * (mincenter * mincenter))
        elif k > 0:
            if bordertype == 'crop':
                return r[0] / s[0]
            else:
                return 1 / (1 + k * (mincenter * mincenter))

    if len(input_array.shape) == 3:
        for i in range(input_array.shape[2]):
            output[:, :, i] = _correct_distortion(input_array[:, :, i], k,bordertype=bordertype,model=model)
    else:
        output = _correct_distortion(input_array, k)
    return output


def applytoimage(input_file, output_file, model, k, bordertype='fit', interpolation='linear', padmethod='symmetric',
                        ftype=2):

    with open(input_file, "rb") as f:
        img = Image.open(f)
        img.load()
        Image.fromarray(
            _lens_distort(np.asarray(img), k, bordertype=bordertype, interpolation=interpolation, padmethod=padmethod,
                          model=model).astype(np.uint8)).save(output_file)

def applytovideo(input_file, output_file, model, k, bordertype='fit', interpolation='linear', padmethod='symmetric',
                        ftype=2):
    cap = cv2api_delegate.videoCapture(input_file)
    fourcc = int(cap.get(cv2api_delegate.fourcc_prop))
    fps = cap.get(cv2api_delegate.prop_fps)
    height = int(np.rint(cap.get(cv2api_delegate.prop_frame_height)))
    width = int(np.rint(cap.get(cv2api_delegate.prop_frame_width)))
    out_video = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
    if not out_video.isOpened():
        err = out_video + " fourcc: " + str(fourcc) + " FPS: " + str(fps) + \
              " H: " + str(height) + " W: " + str(width)
        raise ValueError('Unable to create video ' + err)
    try:
        count = 0
        while (cap.grab()):
            ret, frame = cap.retrieve()
            count += 1
            out_video.write(_lens_distort(frame,k, bordertype=bordertype, interpolation=interpolation, padmethod=padmethod,
                          model=model).astype(np.uint8))
    finally:
        cap.release()
        out_video.release()

def applylensdistortion(input_file, output_file, k, bordertype='fit', interpolation='linear', padmethod='symmetric',
                        ftype=2):
    model = lambda r, k: r * (1 / (1 + k * r))
    if int(ftype) == 2:
        model = lambda r, k: r * (1 / (1 + k * r * r))
    elif int(ftype) == 3:
        model = lambda r, k: r * (1 + k * r)
    elif int(ftype) == 4:
        model = lambda r, k: r * (1 + k * r * r)

    if tool_set.fileType(input_file) == 'image':
        applytoimage(input_file, output_file,model,k,bordertype=bordertype,interpolation=interpolation,padmethod=padmethod,
                     ftype=ftype)
    else:
        applytovideo(input_file, output_file, model, k, bordertype=bordertype, interpolation=interpolation,
                     padmethod=padmethod,
                     ftype=ftype)





def transform(im, source, target, **kwargs):
    k = float(kwargs['threshold'])
    applylensdistortion(source, target,k,
                        ftype=kwargs['model'] if 'model' in kwargs else 4,
                        interpolation=kwargs['interpolation'] if 'interpolation' in kwargs else 'linear',
                        bordertype=kwargs['bordertype'] if 'bordertype' in kwargs else 'fit',
                        padmethod=kwargs['padmethod'] if 'padmethod' in kwargs  else 'fill')
    dt = "Pincushion" if k < 0 else ("Barrel" if k > 0 else "Mustache")
    return {"Distortion Type" : dt}, None

def operation():
    return {
        'name': 'LensDistortion',
        'category': 'AntiForensic',
        'description': 'Apply lens Distortion.',
        'software': 'PAR Lens Distort',
        'version': '0.1',
        'arguments': {
            'threshold': {
                'type': 'float[-1.0:1.0]',
                'defaultValue': '0.25',
                'description': 'Distortion level (-1:1). Use x < 0 for pincushion, x > 0 for barrel (be sure to set distortion type param appropriately).'
            },
            'interpolation': {
                'type': 'list',
                'values': ['linear','nearest','cubic'],
                'defaultValue': 'linear',
                'description': 'Translates to CV2 interpolation (see resize())'
            },
            'padmethod': {
                'type': 'list',
                'values': ['bound', 'symmetric','fill','circular','replicate'],
                'defaultValue': 'fill',
                'description': 'controls how the resamples interpolates or assigns values to elements that map close to or outside the edge of the image'
            },
            'bordertype': {
                'type': 'list',
                'values': ['fit', 'crop'],
                'defaultValue': 'fit',
                'description': 'How to treat edge of image'
            },
            'model': {
                'type': 'list',
                'values': [1,2,3,4],
                'defaultValue': 4,
                'description': 'Models 1 and 2 are sigmoid.  Models 3 and 4 are polynomial degree 1 and 2'
            }
        },
        'transitions': [
            'image.image'
        ]
    }

def suffix():
    return '.png'
