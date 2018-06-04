import cv2
import dlib

# path to pretrained model utilized in face detection
# assumes the model file is in the same directory as this code, please specify full path in case this condition is invalid on user's local machine
import numpy

PREDICTOR_PATH = "pretrained_model.dat"

# pre-defined parameters used by the dlib library towards face detection
SCALE_FACTOR = 1
FEATHER_AMOUNT = 11
FACE_POINTS = list(range(17, 68))
MOUTH_POINTS = list(range(48, 61))
RIGHT_BROW_POINTS = list(range(17, 22))
LEFT_BROW_POINTS = list(range(22, 27))
RIGHT_EYE_POINTS = list(range(36, 42))
LEFT_EYE_POINTS = list(range(42, 48))
NOSE_POINTS = list(range(27, 35))
JAW_POINTS = list(range(0, 17))

# Points used to line up the face patch in donor and recipient images
ALIGN_POINTS = (LEFT_BROW_POINTS + RIGHT_EYE_POINTS + LEFT_EYE_POINTS +
				RIGHT_BROW_POINTS + NOSE_POINTS + MOUTH_POINTS)

# Points from the donor image to overlay on the recipient image
OVERLAY_POINTS = [
	LEFT_EYE_POINTS + RIGHT_EYE_POINTS + LEFT_BROW_POINTS + RIGHT_BROW_POINTS,
	NOSE_POINTS + MOUTH_POINTS,
]

# blur to use during color correction
COLOR_CORRECT_BLUR_FRAC = 0.6

# instantiate objects from dlib library classes for face detection
detector = dlib.get_frontal_face_detector()
predictor = None


class TooManyFaces(Exception):
	pass


class NoFaces(Exception):
	pass


def loadModel(path=None):
	global predictor
	if predictor is None:
		path = PREDICTOR_PATH if path is None else path
		predictor = dlib.shape_predictor(path)


def get_landmarks(im):
	global predictor
	rects = detector(im, 1)

	if len(rects) > 1:
		print('Image seems to have more than one detecable faces present.')
	if len(rects) == 0:
		raise NoFaces

	return numpy.matrix([[p.x, p.y] for p in predictor(im, rects[0]).parts()])


def annotate_landmarks(im, landmarks):
	im = im.copy()
	for idx, point in enumerate(landmarks):
		pos = (point[0, 0], point[0, 1])
		cv2.putText(im, str(idx), pos,
					fontFace=cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
					fontScale=0.4,
					color=(0, 0, 255))
		cv2.circle(im, pos, 3, color=(0, 255, 255))
	return im


def read_im_and_landmarks(fname):
	"""
	Read the computed facial landmarks
	"""
	im = cv2.imread(fname, cv2.IMREAD_COLOR)
	im = cv2.resize(im, (im.shape[1] * SCALE_FACTOR,
						 im.shape[0] * SCALE_FACTOR))
	s = get_landmarks(im)
	return im, s


def draw_convex_hull(im, points, color):
	points = cv2.convexHull(points)
	cv2.fillConvexPoly(im, points, color=color)


def get_face_mask(im, landmarks):
	im = numpy.zeros(im.shape[:2], dtype=numpy.float64)

	for group in OVERLAY_POINTS:
		draw_convex_hull(im,
						 landmarks[group],
						 color=1)

	im = numpy.array([im, im, im]).transpose((1, 2, 0))

	im = (cv2.GaussianBlur(im, (FEATHER_AMOUNT, FEATHER_AMOUNT), 0) > 0) * 1.0
	im = cv2.GaussianBlur(im, (FEATHER_AMOUNT, FEATHER_AMOUNT), 0)

	return im


def transform(img, source, target, **kwargs):
	loadModel(kwargs['model'].strip())
	im2, landmarks2 = read_im_and_landmarks(source)
	mask = get_face_mask(im2, landmarks2)
	im = cv2.imread(source)
	im = numpy.array(im)
	mask[mask > 0.5] = 255
	fin = numpy.concatenate((im, mask[:,:,0:1]), axis=2)
	cv2.imwrite(target, fin)
	return {'subject':'face','location change':'no'}, None


def operation():
	return {'name': 'SelectRegion',
			'category': 'Select',
			'description': 'Select a face based on DLIB trained model',
			'software': 'DLIB',
			'version': '19.9',
			'arguments': {'alpha': {'type': "yesno",
									"defaultvalue": "yes",
									'description': "If yes, save the image with an alpha channel instead of the mask."},
						  'model': {'type': 'text', 'description': 'The face selection model'}},
			'transitions': [
				'image.image'
			]
			}


def suffix():
	return None
