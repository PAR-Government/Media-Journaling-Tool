import os
import logging
from maskgen.tool_set import openImageFile, ImageWrapper
import cv2
import numpy as np


class OpenCVECCRegistration:
    logger = logging.getLogger("maskgen")

    def __init__(self, base_image, **args):
        if type(base_image) == np.ndarray:
            self.base = base_image
            self.name = "base image"
        elif isinstance(base_image, ImageWrapper):
            self.base = base_image.image_array
            self.name = os.path.basename(base_image.filename)
        elif type(base_image) == str:
            wrapper = openImageFile(base_image)
            self.base = wrapper.image_array
            self.name = os.path.basename(wrapper.filename)
        else:
            raise ValueError("Invalid image type: {0}".format(type(base_image)))

    def align(self, image, warp_mode=cv2.MOTION_TRANSLATION):
        if type(image) == np.ndarray:
            m = "Aligning image to " + self.name
            second = image
        elif isinstance(image, ImageWrapper):
            m = "Aligning {0} to {1}".format(os.path.basename(image.filename), self.name)
            second = image.image_array
        elif type(image) == str:
            second_wrapper = openImageFile(image)
            second = second_wrapper.image_array
            m = "Aligning {0} to {1}".format(second_wrapper.filename, self.name)
        else:
            raise ValueError("Invalid image type: {0}".format(type(image)))
        self.logger.debug(m)

        if self.base.shape != second.shape:
            raise ValueError("Shape Mismatch Error: {0} {1}".format(self.base.shape, second.shape))

        # Can use self.base or image when referring to shape, using self.base for consistency
        final = np.empty(self.base.shape)
        alpha = self.base.shape[-1] % 2 == 0 and len(self.base.shape) > 2
        if alpha:
            final[:, :, -1] = image[:, :, -1]

        for channel in range(0, self.base.shape[-1] if not alpha else self.base.shape[-1] - 1):

            if warp_mode == cv2.MOTION_HOMOGRAPHY:
                warp_matrix = np.eye(3, 3, dtype=np.float32)
            else:
                warp_matrix = np.eye(2, 3, dtype=np.float32)

            number_of_iterations = 5000
            termination_eps = 1e-10

            # Define termination criteria
            criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, number_of_iterations, termination_eps)

            # Run the ECC algorithm. The results are stored in warp_matrix.
            (cc, warp_matrix) = cv2.findTransformECC(self.base[:, :, channel],
                                                     second[:, :, channel],
                                                     warp_matrix,
                                                     warp_mode,
                                                     criteria)
            if warp_mode == cv2.MOTION_HOMOGRAPHY:
                # Use warpPerspective for Homography
                cfinal = cv2.warpPerspective(second[:, :, channel], warp_matrix, (self.base.shape[1],
                                             self.base.shape[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
            else:
                # Use warpAffine for Translation, Euclidean and Affine
                cfinal = cv2.warpAffine(second[:, :, channel], warp_matrix, (self.base.shape[1], self.base.shape[0]),
                                        flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
            final[:, :, channel] = cfinal

        return final
