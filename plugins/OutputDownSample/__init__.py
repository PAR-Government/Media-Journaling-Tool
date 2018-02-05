from maskgen.video_tools import x264
import maskgen
"""
Save te image as AVI downsampling as directed.
"""
def transform(img,source,target, **kwargs):

    crf = int(kwargs['crf']) if 'crf' in kwargs else 0
    resolution = int(kwargs['resolution']) if 'resolution' in kwargs else '1280x720'
    resolution = resolution.replace('x',':')
    pixelaspect = kwargs['pixel aspect'] if 'pixel aspect' in kwargs else 'No Change'

    pamap = {
        'No Change':['-s',resolution],
        'Square Pixels (1.0)':['-s',resolution],
        'D1/DV NTSC (0.9091)':['-r','29.97','-vf' 'scale=interl=1,setdar=4:3',
                               '-aspect', '4:3','-acodec', 'copy'],
        'D1/DV NTSC Widescreen 16:9 (1.2121)':
        ['-r','29.97','-vf' 'scale=720:480:lanczos:interl=1:setdar=16/9',
         '-target', 'ntsc-dvd', '-aspect', '16:9','-acodec', 'ac3', '-b:a', '256k'],
        "D1/DV PAL (1.0940)":['-r','25', '-vf' 'scale=720:480:lanczos:interl=1:setdar=4/3',
         '-pix_fmt', 'yuv420p', '-aspect', '4:3','-acodec', 'ac3', '-b:a', '256k'],
        "D1/DV PAL Widescreen 16:9 (1.4587)":['-r','25', '-vf' 'scale=720:576:lanczos:interl=1:setdar=16/9',
         '-pix_fmt', 'yuv420p', '-aspect', '16:9','-acodec', 'ac3', '-b:a', '256k'],
        "Anamorphic 2:1 (2.0)":['-vf','setsar=2:1'],
        "HD Anamorphic 1080 (1.333)":['-s','1440:1080', '-acodec', 'copy'],
        "DVCPRO HD (1.5)":['-s','1280:1080', '-acodec', 'copy'],
        "Custom":['-s',resolution]
    }
    x264(source,outputname=target,crf=crf,additional_args=pamap[pixelaspect])
    return {'pixel aspect':'No Change'},None
    
def operation():
    return {'name':'TransformDownSample',
            'category':'Transform',
            'description':'Save an video as .avi using codec X264. Down sample the video',
            'software':'ffmpeg',
            'version':maskgen.video_tools.get_ffmpeg_version(),
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
