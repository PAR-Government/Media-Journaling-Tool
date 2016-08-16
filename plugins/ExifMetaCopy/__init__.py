from subprocess import call

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    call(['exiftool', '-q','-all=', target])
    call(['exiftool', '-P', '-q', '-m', '-TagsFromFile',  donor[1], '-all:all', '-unsafe', target])
    call(['exiftool', '-P', '-q', '-m', '-XMPToolkit=', target])
    return False

def suffix():
    return '.jpg'

def operation():
    return ['AntiForensicCopyExif','AntiForensicExif','Copy Image EXIF from donor','exiftool','10.23']
  
def args():
    return [('donor', None, 'JPEG with donor EXIF')]
