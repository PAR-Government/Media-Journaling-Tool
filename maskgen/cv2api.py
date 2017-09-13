import cv2

"""
Wrapper class around CV2 to support different API versions (opencv 2 and 3)
"""

class CV2Api:
    def findContours(self,image):
        pass

class CV2ApiV2:
    def findContours(self,image,mode,method):
        contours, hierarchy  = cv2.findContours(image, mode, method)
        return contours,hierarchy

class CV2ApiV3:
    def findContours(self,image,mode,method):
        img2, contours, hierarchy = cv2.findContours(image, mode, method)
        return contours,hierarchy

global cv2api_delegate

cv2api_delegate = CV2ApiV2() if cv2.__version__ .startswith('2') else CV2ApiV3()

def findContours(image,mode,method):
    global cv2api_delegate
    return cv2api_delegate.findContours(image,mode,method)

