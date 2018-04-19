import cv2
import numpy as np
import tensorflow as tf
import tensorlayer as tl
from maskgen.support import getValue
from maskgen.exif import rotateAccordingToExif,getOrientationFromExif

def cfa_sample(ims):
    sampled = np.copy(ims)
    sampled[:, 0::2, 1::2, 0] = 0
    sampled[:, 1::2, 0::2, 0] = 0
    return sampled


def color_cfa_sample(ims):
    sampled = np.copy(ims)
    # blue
    sampled[:, 0::2, 0::2, 0] = 0
    sampled[:, 1::2, 0::2, 0] = 0
    sampled[:, 1::2, 1::2, 0] = 0
    # green
    sampled[:, 0::2, 1::2, 1] = 0
    sampled[:, 1::2, 0::2, 1] = 0
    # red
    sampled[:, 0::2, 0::2, 2] = 0
    sampled[:, 0::2, 1::2, 2] = 0
    sampled[:, 1::2, 1::2, 2] = 0
    return sampled

def divide_image(image):
    s_rowblk = image.shape[0]
    while(s_rowblk % 2== 0 and s_rowblk>300):
        s_rowblk = s_rowblk / 2
    s_rowblk = s_rowblk * 2

    s_colblk=image.shape[1]
    while(s_colblk % 2==0 and s_colblk>300):
        s_colblk =s_colblk / 2
    s_colblk = s_colblk * 2

    n_rowblk=image.shape[0] / s_rowblk
    n_colblk=image.shape[1] / s_colblk

    return n_rowblk,n_colblk,s_rowblk,s_colblk

def generator(image):
    w_init = tf.contrib.layers.xavier_initializer(uniform=False)
    b_init = tf.constant_initializer(value=0.1)

    def conv(im, name, ksiz, stride, nout, bias, act=tf.nn.relu):
        nin = im.get_shape()[-1].value
        with tf.variable_scope(name):
            w = tf.get_variable(name='weight', shape=[ksiz, ksiz, nin, nout], dtype=tf.float32, initializer=w_init)
            conv = tf.nn.conv2d(im, w, [1, stride, stride, 1], padding='SAME')
            if bias:
                b = tf.get_variable(name='bias', shape=[nout], dtype=tf.float32, initializer=b_init)
                out = act(conv + b)
            else:
                out = act(conv)

            return out

    with tf.variable_scope('generator') as scope:

        # w_const = tf.Variable([[0, 0.25, 0], [0.25, 1, 0.25], [0, 0.25, 0]], trainable=True)
        # w_const = tf.reshape(w_const, [3, 3, 1, 1])
        # tf.add_to_collection('w_const',w_const)
        # conv0 = tf.nn.conv2d(image, w_const, [1, 1, 1, 1], padding='SAME', name='conv0')
        # tf.add_to_collection('conv0', conv0)

        conv0 = conv(image, name = 'conv0', ksiz = 3, stride = 1, nout = 3, bias = True, act = tf.nn.relu)
        tf.add_to_collection('conv0',conv0)

        conv1 = conv(conv0, name = 'conv1', ksiz = 3, stride = 1, nout = 64, bias = True, act = tf.nn.relu)
        tf.add_to_collection('conv1', conv1)
        conv2 = conv(conv1, name = 'conv2', ksiz = 3, stride = 1, nout = 64, bias = True, act = tf.nn.relu)
        tf.add_to_collection('conv2', conv2)
        conv3 = conv(conv2, name = 'conv3', ksiz = 1, stride = 1, nout = 64, bias = True, act = tf.nn.relu)
        tf.add_to_collection('conv3', conv3)

        conv4 = conv(conv3, name = 'conv4', ksiz = 3, stride = 1, nout = 128, bias = True, act = tf.nn.relu)
        tf.add_to_collection('conv4', conv4)
        conv5 = conv(conv4, name = 'conv5', ksiz = 3, stride = 1, nout = 128, bias = True, act = tf.nn.relu)
        tf.add_to_collection('conv5', conv5)
        conv6 = conv(conv5, name = 'conv6', ksiz = 1, stride = 1, nout = 128, bias = True, act = tf.nn.relu)
        tf.add_to_collection('conv6', conv6)

        conv7 = conv(conv6, name = 'conv7', ksiz = 3, stride = 1, nout = 3, bias = True, act = tf.nn.relu)
        tf.add_to_collection('conv7', conv7)
    return conv7

def run_model(img, target, model, channel=3, overlap=8):
    input_image = tf.placeholder(tf.float32, [None, None, None, channel], name='input_image')
    gen_out = generator(input_image)

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        tl.files.load_and_assign_npz_dict(name=model, sess=sess)
        nx, ny, sx, sy = divide_image(img)
        gen_im = np.zeros(img.shape)
        for i in range(nx):
            for j in range(ny):
                flag_u = 1
                flag_d = 1
                flag_l = 1
                flag_r = 1
                start_i = i * sx - overlap
                if start_i < 0:
                    flag_u = 0
                    start_i = 0
                end_i = (i + 1) * sx + overlap
                if end_i > img.shape[0]:
                    flag_d = 0
                    end_i = img.shape[0]

                start_j = j * sy - overlap
                if start_j < 0:
                    flag_l = 0
                    start_j = 0
                end_j = (j + 1) * sy + overlap
                if end_j > img.shape[1]:
                    flag_r = 0
                    end_j = img.shape[1]
                batch = img[start_i:end_i, start_j:end_j, :]
                #print start_i, end_i, start_j, end_j
                batch_smp = color_cfa_sample(np.expand_dims(batch, 0))
                gen_batch = sess.run(gen_out, feed_dict={input_image: batch_smp})
                gen_x = gen_batch.shape[1]
                gen_y = gen_batch.shape[2]
                gen_im[i * sx:(i + 1) * sx, j * sy:(j + 1) * sy, :] = gen_batch[0,
                                                                      flag_u * overlap:gen_x - flag_d * overlap,
                                                                      flag_l * overlap:gen_y - flag_r * overlap, :]
        cv2.imwrite(target, gen_im)


def transform(img, source, target, **kwargs):
    rawimage = np.asarray(img)
    if getValue(kwargs,'rotate','no') == 'yes':
        rawimage = rotateAccordingToExif(rawimage,getOrientationFromExif(source),counter=True)
    run_model(rawimage[:,:,0:3],target,kwargs['model'])
    return None, None


def operation():
    return {'name': 'AddCameraModel',
            'category': 'AntiForensic',
            'description': 'Run MATLAB script to correct for double JPG compression and other JPG artifacts.',
            'software': 'DrexelCameraModel',
            'version': '041218',
            'arguments': {
                'model': {
                    'type': 'file:npz',
                    'defaultValue': None,
                    'description': 'Model File'
                },
                'rotate': {
                    'type': 'yesno',
                    'defaultValue': 'yes',
                    'description': 'Model File'
                }
            },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return '.png'
