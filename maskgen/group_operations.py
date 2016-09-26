import plugins
import sys
import exif
from description_dialog import RotateDialog
import tkSimpleDialog


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


class ToJPGGroupOperation(BaseOperation):
    """
     A special group operation used to convert back to JPEG including
     EXIF Copy and Recompression with base image QT
    """

    def __init__(self, scModel):
        BaseOperation.__init__(self, scModel)

    def suffix(self):
        return '.jpg'

    def filterPairs(self, pairs):
        if len(pairs) == 0:
            return pairs
        result = []
        for pair in pairs:
            pred = self.scModel.getDescriptionForPredecessor(pair[0])
            if str(pred.operationName) == 'AntiForensicCopyExif':
                print 'Error: Last operation is ExifMetaCopy. Use CompressAs plugin with base image as donor.'
            else:
                result.append(pair)
        return result

    def performOp(self, master_ui):
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
                if orientation is not None:
                    rotated_im = exif.rotateAccordingToExif(im, orientation)
                    dialog = RotateDialog(master_ui, donor_im, rotated_im, orientation)
                    rotate = dialog.rotate
                msg, pairs = self.scModel.imageFromPlugin('CompressAs', im, filename, donor=pair[1],
                                                          sendNotifications=False, rotate=rotate,
                                                          skipRules=True)
                if len(pairs) == 0:
                    break
                newPairs.extend(pairs)
        return (msg, newPairs)
