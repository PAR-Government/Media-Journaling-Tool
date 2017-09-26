import numpy as np
from PIL import Image


def openRawFile(filename,isMask=None, args=None):
        import rawpy
        with rawpy.imread(filename) as raw:
            if args is not None and 'Bits per Channel' in args:
                bits = int(args['Bits per Channel'])
            else:
                bits = 8
            use_camera_wb = args is not None and \
                            'White Balance' in args and \
                            args['White Balance'] == 'camera'
            use_auto_wb = args is not None and \
                          'White Balance' in args and \
                          args['White Balance'] == 'auto'
            colorspace = rawpy.ColorSpace.raw
            if args is not None and 'Color Space' in args:
                v = args['Color Space']
                cs_mapping = {'Adobe': rawpy.ColorSpace.Adobe,
                              'sRGB': rawpy.ColorSpace.sRGB,
                              'XYZ': rawpy.ColorSpace.XYZ,
                              'Wide': rawpy.ColorSpace.Wide,
                              'ProPhoto': rawpy.ColorSpace.ProPhoto,
                              'default': rawpy.ColorSpace.raw
                              }
                colorspace = cs_mapping[v]
            if args is not None and 'Demosaic Algorithm' in args and args['Demosaic Algorithm'] != 'default':
                v = args['Demosaic Algorithm']
                mapping = {'AAHD': rawpy.DemosaicAlgorithm.AAHD,
                           'AFD': rawpy.DemosaicAlgorithm.AFD,
                           'AMAZE': rawpy.DemosaicAlgorithm.AMAZE,
                           'DCB': rawpy.DemosaicAlgorithm.DCB,
                           'DHT': rawpy.DemosaicAlgorithm.DHT,
                           'LMMSE': rawpy.DemosaicAlgorithm.LMMSE,
                           'MODIFIED_AHD': rawpy.DemosaicAlgorithm.MODIFIED_AHD,
                           'PPG': rawpy.DemosaicAlgorithm.PPG,
                           'VCD': rawpy.DemosaicAlgorithm.VCD,
                           'LINEAR': rawpy.DemosaicAlgorithm.LINEAR,
                           'VCD_MODIFIED_AHD': rawpy.DemosaicAlgorithm.VCD_MODIFIED_AHD,
                           'VNG': rawpy.DemosaicAlgorithm.VNG}
                return raw.postprocess(demosaic_algorithm=mapping[v],
                                                    output_bps=bits,
                                                    use_camera_wb=use_camera_wb,
                                                    use_auto_wb=use_auto_wb,
                                                    output_color=colorspace),'RGB'

            return raw.postprocess(output_bps=bits,
                                                use_camera_wb=use_camera_wb,
                                                use_auto_wb=use_auto_wb,
                                                output_color=colorspace),'RGB'

def openRawFileOld(filename,isMask=None, args=None):
    from rawkit.raw import Raw
    from rawkit.options import WhiteBalance,colorspaces,interpolation
    if args is not None and 'Bits per Channel' in args:
        bits = int(args['Bits per Channel'])
    else:
        bits = 8
    use_camera_wb = args is not None and \
                    'White Balance' in args and \
                    args['White Balance'] == 'camera'
    use_auto_wb = args is not None and \
                  'White Balance' in args and \
                  args['White Balance'] == 'auto'
    colorspace_v = colorspaces.raw
    if args is not None and 'Color Space' in args:
        v = args['Color Space']
        cs_mapping = {'Adobe': colorspaces.colorspaces,
                      'sRGB': colorspaces.srgb,
                      'XYZ': colorspaces.xyz,
                      'Wide': colorspaces.wide_gammut_rgb,
                      'ProPhoto': colorspaces.kodak_prophoto_rgb,
                      'default': colorspaces.raw
                      }
        colorspace_v = cs_mapping[v]
    interpolation_v=interpolation.linear
    if args is not None and 'Demosaic Algorithm' in args and args['Demosaic Algorithm'] != 'default':
        v = args['Demosaic Algorithm']
        mapping = {'AAHD': interpolation.ahd,
                   'AFD': interpolation.afd,
                   'AMAZE': interpolation.amaze,
                   'DCB': interpolation.dcb,
                   'DHT': interpolation.ahd,
                   'LMMSE': interpolation.lmmse,
                   'MODIFIED_AHD': interpolation.modified_ahd,
                   'PPG': interpolation.ppg,
                   'VCD': interpolation.vcd,
                   'LINEAR': interpolation.linear,
                   'VCD_MODIFIED_AHD': interpolation.mixed_vcd_modified_ahd,
                   'VNG': interpolation.vng}
        interpolation_v = mapping[v]
    with Raw(filename=filename) as raw_image:
        raw_image.options.bps=bits
        raw_image.options.interpolation = interpolation_v
        raw_image.options.colorspace =colorspace_v
        raw_image.options.white_balance = WhiteBalance(camera=use_camera_wb, auto=use_auto_wb)
        buffered_image = np.array(raw_image.to_buffer())
        return (np.array(Image.frombytes('RGB',
                                         (raw_image.metadata.height, raw_image.metadata.width), buffered_image)),'RGB')
