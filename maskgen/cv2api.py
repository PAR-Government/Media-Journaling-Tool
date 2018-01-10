import cv2

"""
Wrapper class around CV2 to support different API versions (opencv 2 and 3)
"""

class CV2Api:
    def __init__(self):
        pass

    def findContours(self,image):
        pass

    def videoCapture(self,filename, preference = None):
        if preference is not None:
            return cv2.VideoCapture(filename,preference)
        return cv2.VideoCapture(filename)

    def computeSIFT(self, img):
        None, None

    def get_fourcc(self, codec):
        return 0

class CV2ApiV2(CV2Api):

    def __init__(self):
        CV2Api.__init__(self)
        self.prop_pos_msec = cv2.cv.CV_CAP_PROP_POS_MSEC
        #self.prop_buffer_size = cv2.cv.CV_CAP_PROP_BUFFERSIZE
        self.prop_frame_height = cv2.cv.CV_CAP_PROP_FRAME_HEIGHT
        self.prop_frame_width = cv2.cv.CV_CAP_PROP_FRAME_WIDTH
        self.prop_fps = cv2.cv.CV_CAP_PROP_FPS
        self.prop_frame_count = cv2.cv.CV_CAP_PROP_FRAME_COUNT
        self.tm_sqdiff_normed = cv2.cv.CV_TM_SQDIFF_NORMED
        self.tm_ccorr_normed = cv2.cv.CV_TM_CCORR_NORMED
        self.fourcc_prop = cv2.cv.CV_CAP_PROP_FOURCC
        self.inter_linear = cv2.cv.CV_INTER_LINEAR
        self.inter_cubic = cv2.cv.CV_INTER_CUBIC
        self.inter_nn = cv2.INTER_NEAREST
        self.inter_area = cv2.INTER_AREA
        self.inter_lanczos = cv2.INTER_LANCZOS4

    def findContours(self,image,mode,method):
        contours, hierarchy  = cv2.findContours(image, mode, method)
        return contours,hierarchy

    def computeSIFT(self, img):
        detector = cv2.FeatureDetector_create("SIFT")
        extractor = cv2.DescriptorExtractor_create("SIFT")
        kp = detector.detect(img)
        return extractor.compute(img, kp)

    def get_fourcc(self,codec):
        if codec == '0' or codec == 0:
            return 0
        return cv2.cv.CV_FOURCC(*codec)


class CV2ApiV3(CV2Api):

    def __init__(self):
        CV2Api.__init__(self)
        self.prop_pos_msec = cv2.CAP_PROP_POS_MSEC
        #self.prop_buffer_size = cv2.CAP_PROP_BUFFERSIZE
        self.prop_frame_height = cv2.CAP_PROP_FRAME_HEIGHT
        self.prop_frame_width = cv2.CAP_PROP_FRAME_WIDTH
        self.prop_fps = cv2.CAP_PROP_FPS
        self.prop_frame_count = cv2.CAP_PROP_FRAME_COUNT
        self.tm_sqdiff_normed = cv2.TM_SQDIFF_NORMED
        self.tm_ccorr_normed = cv2.TM_CCORR_NORMED
        self.fourcc = cv2.CAP_PROP_FOURCC
        self.inter_linear = cv2.INTER_LINEAR
        self.inter_cubic = cv2.INTER_CUBIC
        self.inter_nn = cv2.INTER_NEAREST
        self.inter_area = cv2.INTER_AREA
        self.inter_lanczos = cv2.INTER_LANCZOS4

    def findContours(self,image,mode,method):
        img2, contours, hierarchy = cv2.findContours(image, mode, method)
        return contours,hierarchy

    def computeSIFT(self, img):
        detector = cv2.xfeatures2d.SIFT_create()
        return detector.detectAndCompute(img,None)

    def get_fourcc(self, codec):
        if codec == '0' or codec == 0:
            return 0
        return cv2.VideoWriter_fourcc(*codec)

global cv2api_delegate

cv2api_delegate = CV2ApiV2() if cv2.__version__ .startswith('2') else CV2ApiV3()

def findContours(image,mode,method):
    global cv2api_delegate
    return cv2api_delegate.findContours(image,mode,method)

