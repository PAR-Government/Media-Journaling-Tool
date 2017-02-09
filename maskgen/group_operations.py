import plugins
import sys
import exif
import numpy as np
import tool_set


class BaseOperation:
    scModel = None
    pairs = []

    def __init__(self, scModel):
        self.scModel = scModel
        self.pairs = self.filterPairs(self.scModel.getTerminalToBasePairs(suffix=self.suffix()))

    def filterPairs(self, pairs):
        return pairs

    def suffix(self):
        return ''


class CopyCompressionAndExifGroupOperation(BaseOperation):
    """
     A special group operation used to convert back to JPEG including
     EXIF Copy and Recompression with base image QT
    """

    def __init__(self, scModel):
        BaseOperation.__init__(self, scModel)

    def suffix(self):
        return ''

    def filterPairs(self, pairs):
        if len(pairs) == 0:
            return pairs
        result = []
        for pair in pairs:
            pred = self.scModel.getDescriptionForPredecessor(pair[0])
            if str(pred.operationName) .startswith('AntiForensicExif'):
                print 'Error: Last operation is ExifMetaCopy. Use CompressAs plugin with base image as donor.'
            else:
                result.append(pair)
        return result

    def performOp(self, promptFunc=None):
        """
          Return error message valid link pairs in a tuple
        """
        newPairs = []
        msg = None
        if not self.pairs:
            msg = 'Could not find paths from base to terminal nodes where the the last operation is not ExifMetaCopy.'
            newPairs = None
        else:
            for pair in self.pairs:
                self.scModel.selectImage(pair[0])
                im, filename = self.scModel.getImageAndName(pair[0])
                donor_im, donor_filename = self.scModel.getImageAndName(pair[1])
                orientation = exif.getOrientationFromExif(donor_filename)
                rotate = 'no'
                if orientation is not None and promptFunc is not None:
                    rotated_im = tool_set.ImageWrapper(exif.rotateAccordingToExif(np.asarray(im), orientation))
                    rotate = promptFunc(donor_im, rotated_im, orientation)
                elif orientation is not None:
                    rotated_im = tool_set.ImageWrapper(exif.rotateAccordingToExif(np.asarray(im), orientation))
                    width1, height1 = im.size
                    width2, height2 = rotated_im.size
                    r1 = abs(width1/height1) < 1
                    r2 = abs(width2/height2) < 1
                    if r1 != r2:
                        rotate = 'yes'
                if donor_filename.lower().endswith('jpg') or donor_filename.lower().endswith('jpeg'):
                    msg, pairs = self.scModel.imageFromPlugin('CompressAs', im, filename, donor=pair[1],
                                                          sendNotifications=False, rotate=rotate,
                                                          skipRules=True)
                elif donor_filename.lower().endswith('tiff') or donor_filename.lower().endswith('tif'):
                    msg, pairs = self.scModel.imageFromPlugin('OutputTIFF', im, filename, donor=pair[1],
                                                                  sendNotifications=False, rotate=rotate,
                                                                  skipRules=True)
                else:
                    pairs = []
                    msg = 'Group operation not permitted for base image nodes that are not JPEG or TIFF'
                if len(pairs) == 0:
                    break
                newPairs.extend(pairs)
        return (msg, newPairs)
