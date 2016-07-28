from subprocess import call

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    call(['exiftool', '-all=', target])
    call(['exiftool', '-P', '-TagsFromFile',  donor[1], '-all:all', '-unsafe', target])
    call(['exiftool', '-XMPToolkit=', target])
    call(['exiftool', '-Warning=', target])
    return False

def operation():
    return ['AntiForensicCopyExif','AntiForensicExif','Copy Image EXIF from donor','exiftool','10.23']
  
def args():
    return [('donor', None)]
