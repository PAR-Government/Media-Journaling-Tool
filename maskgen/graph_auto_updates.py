from image_graph import current_version
import tool_set
import os
import logging

def updateJournal(scModel):
    """
     Apply updates
     :param scModel: Opened project model
     :return: None. Updates JSON.
     @type scModel: ImageProjectModel
    """
    upgrades = scModel.getGraph().getDataItem('jt_upgrades')
    upgrades = upgrades if upgrades is not None else []
    if "0.3.1115" not in upgrades:
        _fixRecordMasInComposite(scModel)
        _replace_oldops(scModel)
        upgrades.append('0.3.1115')
    if  "0.3.1213" not in upgrades:
        _fixQT(scModel)
        _fixUserName(scModel)
        upgrades.append('0.3.1213')
    if  "0.4.0101" not in upgrades:
        upgrades.append('0.4.0101')
    if  "0.4.0101.8593b8f323" not in upgrades:
        _fixResize(scModel)
        _fixResolution(scModel)
        upgrades.append('0.4.0101.8593b8f323')
    if "0.4.0308.f7d9a62a7e" not in upgrades:
        _fixLabels(scModel)
        upgrades.append('0.4.0308.f7d9a62a7e')
    if "0.4.0308.dd9555e4ba" not in upgrades:
        _fixPasteSpliceMask(scModel)
        upgrades.append('0.4.0308.dd9555e4ba')
    if "0.4.0308.90e0ce497f" not in upgrades:
        _fixTransformCrop(scModel)
        upgrades.append('0.4.0308.90e0ce497f')
    if "0.4.0308.adee798679" not in upgrades:
        _fixEdgeFiles(scModel)
        _fixBlend(scModel)
        upgrades.append('0.4.0308.adee798679')
    if "0.4.0308.db2133eadc" not in upgrades:
        _fixFileArgs(scModel)
        upgrades.append('0.4.0308.db2133eadc')
    if "0.4.0425.d3bc2f59e1" not in upgrades:
        _operationsChange1(scModel)
        upgrades.append('0.4.0425.d3bc2f59e1')
    if '0.4.0101.b4561b475b' not in upgrades:
        _fixCreator(scModel)
        _fixValidationTime(scModel)
        upgrades.append('0.4.0101.b4561b475b')
    if '04.0621.3a5c9635ef' not in upgrades:
        _fixProvenanceCategory(scModel)
        upgrades.append('04.0621.3a5c9635ef')
    if scModel.getGraph().getVersion() not in upgrades:
        upgrades.append(scModel.getGraph().getVersion())
    scModel.getGraph().setDataItem('jt_upgrades',upgrades,excludeUpdate=True)
    if scModel.getGraph().getDataItem('autopastecloneinputmask') is None:
        scModel.getGraph().setDataItem('autopastecloneinputmask','no')

def _fixValidationTime(scModel):
    import time
    validationdate = scModel.getProjectData('validationdate')
    if validationdate is not None and len(validationdate) > 0:
        scModel.setProjectData('validationtime',time.strftime("%H:%M:%S"),excludeUpdate=True)

def _fixProvenanceCategory(scModel):
    from maskgen.graph_rules import  manipulationCategoryRule
    cat = scModel.getProjectData('manipulationcategory',default_value='')
    if cat.lower() == 'provenance':
        scModel.setProjectData('provenance','yes')
    else:
        scModel.setProjectData('provenance', 'no')
    scModel.setProjectData('manipulationcategory',manipulationCategoryRule(scModel,None))

def _operationsChange1(scModel):
    projecttype = scModel.G.getDataItem('projecttype')
    from image_graph import setPathValue
    blur_type_mapping = {
        'AdditionalEffectFilterBlur':'Other',
        'AdditionalEffectFilterSmoothing':'Smooth',
        'FilterBlurMotion':'Motion',
        'AdditionalEffectFilterMedianSmoothing':'Median Smoothing',
    }
    laundering_type_mapping = {
        'AdditionalEffectFilterBlur': 'no',
        'AdditionalEffectFilterSmoothing': 'yes',
        'FilterBlurMotion': 'no',
        'AdditionalEffectFilterMedianSmoothing': 'yes',
    }
    fill_category_mapping = {
        'ColorFill': 'uniform color',
        'FillPattern': 'pattern',
        'FillPaintBucket': 'uniform color',
        'FillLocalRetouching': 'paint brush',
        'FillBackground': 'paint brush',
        'FillForeground': 'paint brush',
        'AdditionalEffectSoftEdgeBrushing': 'paint brush',
        'FillPaintBrushTool': 'paint brush'
    }
    source_mapping = {
        'ColorReplace': 'self',
        'ColorHue': 'other',
        'ColorMatch': 'self'
    }
    direction_mapping = {
        'ColorSaturation': 'increase',
        'ColorVibranceContentBoosting': 'increase',
        'IntensityDesaturate': 'decrease',
        'ColorVibranceReduction': 'decrease',
        'IntensityBrightness':'increase',
        'IntensityDodge':'increase',
        'IntensityHighlight':'increase',
        'IntensityLighten': 'increase',
        'IntensityDarken':'decrease',
        'IntensityBurn':'decrease'
        }
    noise_mapping = {
        'FilterBlurNoise': 'other',
        'AdditionalEffectFilterAddNoise': 'other'
    }
    op_mapping = {
        'AdditionalEffectAddLightSource':'ArtificialLighting',
        'AdditionalEffectFading':'Fading',
        'AdditionalEffectMosaic':'Mosaic',
        'AdditionalEffectReduceInterlaceFlicker':'ReduceInterlaceFlicker',
        'AdditionalEffectWarpStabilize':'WarpStabilize',
        'AdditionalEffectFilterBlur':'Blur',
        'AdditionalEffectFilterSmoothing':'Blur',
        'AdditionalEffectFilterMedianSmoothing':'Blur',
        'AdditionalEffectFilterSharpening':'Sharpening',
        'AdditionalEffectGradientEffect':'Gradient',
        'AdditionalEffectFilterAddNoise':'AddNoise',
        'FilterBlurNoise':'AddNoise',
        'AdditionalEffectSoftEdgeBrushing':'CGIFill',
        'FilterBlurMotion':'MotionBlur',
        'CreationFilterGT':'CreativeFilter',
        'ArtifactsCGIArtificialReflection':'ArtificialReflection',
        'ArtifactsCGIArtificialShadow':'ArtificialShadow',
        'ArtifactsCGIObjectCGI':'ObjectCGI',
        'ColorFill':'CGIFill',
        'ColorReplace':'Hue',
        'ColorHue':'Hue',
        'ColorMatch':'Hue',
        'ColorVibranceContentBoosting':'Vibrance',
        'ColorVibranceReduction':'Vibrance',
        'IntensityDesaturate':'Saturation',
        'ColorSaturation':'Saturation',
        'FillBackground':'CGIFill',
        'FillForeground':'CGIFill',
        'FillGradient':'Gradient',
        'FillPattern':'CGIFill',
        'FillPaintBrushTool':'CGIFill',
        'FillLocalRetouching':'CGIFill',
        'FillPaintBucket':'CGIFill',
        'FillContentAwareFill':'ContentAwareFill',
        'FilterCameraRawFilter':'CameraRawFilter',
        'FilterColorLUT':'ColorLUT',
        'IntensityBrightness':'Exposure',
        'IntensityDarken': 'Exposure',
        'IntensityLighten': 'Exposure',
        'IntensityHighlight': 'Exposure',
        'IntensityNormalization':'Normalization',
        'IntensityBurn': 'Exposure',
        'IntensityExposure':'Exposure',
        'IntensityDodge': 'Exposure',
        'IntensityLevels':'Levels',
        'IntensityContrast':'Contrast',
        'IntensityCurves':'Curves',
        'IntensityLuminosity':'Luminosity',
        'IntensityExposure': 'Exposure',
        'MarkupDigitalPenDraw':'DigitalPenDraw',
        'MarkupHandwriting':'Handwriting',
        'MarkupOverlayObject': 'OverlayObject',
        'MarkupOverlayText':'OverlayText',
        'AdditionalEffectAddTransitions':'AddTransitions'
    }
    groups = scModel.G.getDataItem('groups')
    if groups is None:
        groups = {}
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in groups:
            ops = groups[edge['op']]
        else:
            ops = [edge['op']]
        for op in ops:
            if op in blur_type_mapping:
                setPathValue(edge,'arguments.Blur Type', blur_type_mapping[op])
            if op in noise_mapping:
                setPathValue(edge, 'arguments.Noise Type', noise_mapping[op])
            if op in fill_category_mapping:
                setPathValue(edge,'arguments.Fill Category', fill_category_mapping[op])
            if op in laundering_type_mapping:
                setPathValue(edge,'arguments.Laundering', laundering_type_mapping[op])
            if op in direction_mapping:
                setPathValue(edge,'arguments.Direction', direction_mapping[op])
            if op in source_mapping:
                setPathValue(edge,'arguments.Source', source_mapping[op])
            if projecttype == 'video' and op == 'FilterBlurMotion':
                edge['op'] = 'MotionBlur'
            elif op in op_mapping:
                edge['op'] = op_mapping[op]
        newgroups = {}
        for k,v in groups.iteritems():
            newgroups[k] = [op_mapping[op] if op in op_mapping else op for op in v]
        scModel.G.setDataItem('groups', newgroups)

def _pasteSpliceBlend(scModel):
    import copy
    from group_filter import GroupFilterLoader
    gfl = GroupFilterLoader()
    scModel.G.addEdgeFilePath('arguments.Final Image', 'inputmaskownership')
    grp = gfl.etGroup('PasteSpliceBlend')
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'pastemask'  in edge and edge['pastemask'] is not None:
            args = copy.copy(edge['arguments'])
            args['inputmaskname'] = os.path.joint(scModel.get_dir(),os.path.split(args['pastemask'])[1])
            args['Final Image'] = os.path.joint(scModel.get_dir(),scModel.G.get_node(to)['file'])
            donors = [pred for pred in scModel.G.predecessors() if pred != frm]
            if len(donors) > 0:
                args['donor'] = donors[0]
            args['sendNotifications'] = False
            mod = scModel.getModificationForEdge(frm,to,edge)
            scModel.imageFromGroup(grp, software=mod.software, **args)


def _fixLabels(scModel):
    for node in scModel.getNodeNames():
        scModel.labelNodes(node)

def _fixFileArgs(scModel):
    #  add all the known file paths for now
    # rather than trying to find out which ones were actually used.
    scModel.G.addEdgeFilePath('arguments.XMP File Name','')
    scModel.G.addEdgeFilePath('arguments.qtfile', '')
    scModel.G.addEdgeFilePath('arguments.pastemask', '')
    scModel.G.addEdgeFilePath('arguments.PNG File Name', '')
    scModel.G.addEdgeFilePath('arguments.convolutionkernel', '')
    scModel.G.addEdgeFilePath('inputmaskname', 'inputmaskownership')
    scModel.G.addEdgeFilePath('selectmasks.mask', '')
    scModel.G.addEdgeFilePath('videomasks.videosegment', '')
    scModel.G.addNodeFilePath('compositemaskname', '')
    scModel.G.addNodeFilePath('donors.*', '')

def _fixEdgeFiles(scModel):
    import shutil
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'inputmaskname'  in edge and edge['inputmaskname'] is not None:
            edge['inputmaskname'] = os.path.split(edge['inputmaskname'])[1]
        arguments = edge['arguments'] if 'arguments' in edge  else None
        if arguments is not None:
            for id in ['XMP File Name','qtfile','pastemask','PNG File Name','convolutionkernel']:
                if id in arguments:
                   arguments[id] = os.path.split(arguments[id])[1]
                   fullfile = os.path.join('plugins/JpgFromCamera/QuantizationTables',arguments[id])
                   if os.path.exists(fullfile):
                       shutil.copy(fullfile,os.path.join(scModel.get_dir(),arguments[id]))

def _fixCreator(scModel):
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    modifications = sorted(scModel.getDescriptions(), key=lambda mod: mod.ctime, reverse=False)
    if len(modifications) > 0:
       scModel.getGraph().setDataItem('creator',modifications[0].username,excludeUpdate=True)

def _fixBlend(scModel):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'].lower() == 'blendhardlight':
            edge['op'] = 'Blend'
            if 'arguments' not in edge:
                edge['arguments'] = {'mode' : 'Hard Light'}
            else:
                edge['arguments']['mode']  = 'Hard Light'
        elif edge['op'].lower() == 'blendsoftlight':
            edge['op'] = 'Blend'
            if 'arguments' not in edge:
                edge['arguments'] = {'mode' : 'Soft Light'}
            else:
                edge['arguments']['mode']  = 'Soft Light'

def _fixTransformCrop(scModel):
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'TransformCrop':
            if 'location' not in edge or \
                edge['location'] == "(0, 0)":
                scModel.select((frm,to))
                try:
                    scModel.reproduceMask()
                except Exception as e:
                    'Failed repair of TransformCrop ' + frm + " to " + to + ": " + str(e)

def _fixResolution(scModel):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'arguments' in edge and 'scale'  in edge['arguments']:
            edge['arguments']['resolution'] = edge['arguments']['scale'].replace(':','x')

def _fixResize(scModel):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'TransformResize':
            if 'arguments' not in edge:
                edge['arguments'] = {}
            if 'interpolation' not in edge['arguments']:
                edge['arguments']['interpolation']  = 'other'

def _fixPasteSpliceMask(scModel):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'PasteSplice':
            if 'inputmaskname' in edge and edge['inputmaskname'] is not None:
                if 'arguments' not in edge:
                    edge['arguments']  = {}
                edge['arguments']['pastemask'] = edge['inputmaskname']
                edge.pop('inputmaskname')
                if 'inputmaskownership' in edge:
                    edge.pop('inputmaskownership')


def _fixUserName(scModel):
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    if scModel.getGraph().getDataItem('username') is not None:
        scModel.getGraph().setDataItem('username',scModel.getGraph().getDataItem('username').lower())

def _fixQT(scModel):
    """
      :param scModel:
      :return:
      @type scModel: ImageProjectModel
      """
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'arguments' in edge and 'QT File Name' in edge['arguments']:
            edge['arguments']['qtfile'] = os.path.split(edge['arguments']['QT File Name'])[1]
            edge['arguments'].pop('QT File Name')

def _fixTransforms(scModel):
    """
       Replace true value with  'yes'
       :param scModel: Opened project model
       :return: None. Updates JSON.
       @type scModel: ImageProjectModel
       """
    validatedby = scModel.getProjectData('validatedby')
    if  validatedby is not None and len(validatedby) > 0:
        return
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in ['TransformContentAwareScale','TransformAffine','TransformDistort','TransformMove',
            'TransformScale','TransformShear','TransformSkew','TransformWarp'] and \
                'transform matrix' not in edge :
            scModel.select((frm,to))
            try:
               tool_set.forcedSiftAnalysis(edge,scModel.getImage(frm),scModel.getImage(to),scModel.maskImage(),
                                        linktype=scModel.getLinkType(frm,to))
            except Exception as e:
                logging.warning("Cannot fix SIFT transforms during upgrade: " + str(e))
                logging.warning("Transform not composed for link {} to {}".format( frm, to))

def _fixRecordMasInComposite(scModel):
    """
    Replace true value with  'yes'
    :param scModel: Opened project model
    :return: None. Updates JSON.
    @type scModel: ImageProjectModel
    """
    for frm, to in scModel.G.get_edges():
         edge = scModel.G.get_edge(frm, to)
         if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'true':
            edge['recordMaskInComposite'] = 'yes'

def _replace_oldops(scModel):
    """
    Replace selected operations
    :param scModel: Opened project model
    :return: None. Updates JSON.
    @type scModel: ImageProjectModel
    """
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        oldOp = currentLink['op']
        if oldOp == 'ColorBlendDissolve':
            currentLink['op'] = 'Blend'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            currentLink['arguments']['mode'] = 'Dissolve'
        elif oldOp == 'ColorBlendMultiply':
            currentLink['op'] = 'Blend'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            currentLink['arguments']['mode'] = 'Multiply'
        elif oldOp == 'ColorColorBalance':
            currentLink['op'] = 'ColorBalance'
        elif oldOp == 'ColorMatchColor':
            currentLink['op'] = 'ColorMatch'
        elif oldOp == 'ColorReplaceColor':
            currentLink['op'] = 'ColorReplace'
        elif oldOp == 'IntensityHardlight':
            currentLink['op'] = 'BlendHardlight'
        elif oldOp == 'IntensitySoftlight':
            currentLink['op'] = 'BlendSoftlight'
        elif oldOp == 'FillImageInterpolation':
            currentLink['op'] = 'ImageInterpolation'
        elif oldOp == 'ColorBlendColorBurn':
            currentLink['op'] = 'IntensityBurn'
        elif oldOp == 'FillInPainting':
            currentLink['op'] = 'MarkupDigitalPenDraw'
        elif oldOp == 'FillLocalRetouching':
            currentLink['op'] = 'PasteSampled'
            currentLink['recordMaskInComposite'] = 'true'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            currentLink['arguments']['purpose'] = 'heal'