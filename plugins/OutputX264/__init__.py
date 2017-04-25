from maskgen.video_tools import x264
"""
Save te image as MP4 using X264 loss encoding.
"""
def transform(img,source,target, **kwargs):

    crf = int(kwargs['crf']) if 'crf' in kwargs else 0
    x264(source,outputname=target,crf=crf)
    return None,None
    
def operation():
    return {'name':'OutputAVI',
            'category':'Output',
            'description':'Save an video as .mp4 using codec X264',
            'software':'PIL',
            'version':'1.1.7',
            'arguments':{
                'crf':{
                    'type':'int[0:100]',
                    'defaultvalue':'0',
                    'description':'Constraint Rate Factor. 0 is lossless'
                }
            },
            'transitions': [
                'video.video'
            ]
        }

def suffix():
    return '.avi'
