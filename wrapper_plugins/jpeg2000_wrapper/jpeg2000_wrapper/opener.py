
def openJPeg2000File(filename,isMask=None):
    import glymur
    jp2 = glymur.Jp2k(filename)
    return jp2[:],'JP2'

def writeJPeg2000File(filename,img):
    import glymur
    glymur.Jp2k(filename, data=img)