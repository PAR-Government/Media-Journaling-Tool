import maskgen.exif
import maskgen.video_tools

def save_as_video(source, target, donor):
    """
    Saves image file using quantization tables
    :param source: string filename of source image
    :param target: string filename of target (result). target should have same extension as donor.
    :param donor: string filename of donor MP4
    """

    maskgen.video_tools.runffmpeg(['-i', source, '-y', target])

    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor, '-all:all', '-unsafe', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-XMPToolkit=', target])
    createtime = maskgen.exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        maskgen.exif.runexif(['-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target])

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    save_as_video(source, target, donor)
    
    return None,None
    
def operation():
    return {'name':'AntiForensicCopyExif',
            'category':'AntiForensic',
            'description':'Convert video to donor filetype and copy metadata.',
            'software':'ffmpeg',
            'version':'2.8.4',
            'arguments':{
                'donor':{
                    'type':'donor',
                    'defaultvalue':None,
                    'description':'Video with desired metadata'
                }
            },
            'transitions':[
                'video.video'
            ]
            }

def suffix():
    return 'donor'
