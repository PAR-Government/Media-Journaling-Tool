from image_graph import current_version
import tool_set
import os
from group_filter import getOperationWithGroups

def updateJournal(scModel):
    """
     Apply updates
     :param scModel: Opened project model
     :return: None. Updates JSON.
     @type scModel: ImageProjectModel
    """
    upgrades = scModel.getGraph().getDataItem('jt_upgrades')
    upgrades = upgrades if upgrades is not None else []
    if scModel.G.getVersion() <= "0.3.1115" and "0.3.1115" not in upgrades:
        _fixRecordMasInComposite(scModel)
        _replace_oldops(scModel)
        _fixTransforms(scModel)
        upgrades.append('0.3.1115')
    if scModel.G.getVersion() <= "0.3.1213" and "0.3.1213" not in upgrades:
        _fixQT(scModel)
        _fixUserName(scModel)
        upgrades.append('0.3.1213')
    if scModel.G.getVersion() <= "0.4.0101" and "0.4.0101" not in upgrades:
        _fixTransforms(scModel)
        upgrades.append('0.4.0101')
    if  "0.4.0101.8593b8f323" not in upgrades:
        _fixResize(scModel)
        _fixResolution(scModel)
        upgrades.append('0.4.0101.8593b8f323')
    if '0.4.0101.b4561b475b' not in upgrades:
        _fixCreator(scModel)
        _fixValidationTime(scModel)
        upgrades.append('0.4.0101.b4561b475b')
    if "0.4.0101.52bb2811db" not in upgrades:
        _fixBlend(scModel)
        upgrades.append('0.4.0101.52bb2811db')
    if "0.4.0308.f7d9a62a7e" not in upgrades:
        _fixLabels(scModel)
        upgrades.append('0.4.0308.f7d9a62a7e')
    if "0.4.0308.dd9555e4ba" not in upgrades:
        _fixPasteSpliceMask(scModel)
        upgrades.append('0.4.0308.dd9555e4ba')
    scModel.getGraph().setDataItem('jt_upgrades',upgrades,excludeUpdate=True)
    if scModel.getGraph().getDataItem('autopastecloneinputmask') is None:
        scModel.getGraph().setDataItem('autopastecloneinputmask','no')

def _fixValidationTime(scModel):
    import time
    validationdate = scModel.getProjectData('validationdate')
    if validationdate is not None and len(validationdate) > 0:
        scModel.setProjectData('validationtime',time.strftime("%H:%M:%S"),excludeUpdate=True)

def _fixLabels(scModel):
    for node in scModel.getNodeNames():
        scModel.labelNodes(node)

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
        if edge['op'] == 'BlendHardLight':
            edge['op'] = 'Blend'
            if 'arguments' not in edge:
                edge['arguments'] = {'mode' : 'Hard Light'}
            else:
                edge['arguments']['mode']  = 'Hard Light'
        elif edge['op'] == 'BlendSoftLight':
            edge['op'] = 'Blend'
            if 'arguments' not in edge:
                edge['arguments'] = {'mode' : 'Soft Light'}
            else:
                edge['arguments']['mode']  = 'Soft Light'

def _fixResolution(scModel):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'arguments' in edge and 'scale'  in edge['arguments']:
            edge['arguments']['resolution'] = edge['arguments']['scale'].replace(':','x')

def _fixResize(scModel):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op = getOperationWithGroups(edge['op'], fake=True)
        if op.name == 'TransformResize':
            if 'arguments' not in edge:
                edge['arguments'] = {}
            if 'interpolation' not in edge['arguments']:
                edge['arguments']['interpolation']  = 'other'

def _fixPasteSpliceMask(scModel):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op = getOperationWithGroups(edge['op'], fake=True)
        if op.name == 'PasteSplice':
            if 'inputmaskname' in edge and edge['inputmaskname'] is not None:
                edge['arguments']['pastemask'] = edge['inputmaskname']
                edge.pop('inputmaskname')
                if 'inputmaskownership' in edge:
                    edge.pop('inputmaskownership')

def _fixTransforms(scModel):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op = getOperationWithGroups(edge['op'], fake=True)
        if op.category in 'Transform' and edge['recordMaskInComposite'] == 'yes':
            edge['recordMaskInComposite']= 'no'

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
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in ['TransformContentAwareScale','TransformAffine','TransformDistort','TransformMove','TransformResize',
            'TransformScale','TransformShear','TransformSkew','TransformWarp'] and \
                'transform matrix' not in edge :
            scModel.select((frm,to))
            try:
               tool_set.forcedSiftAnalysis(edge,scModel.getImage(frm),scModel.getImage(to),scModel.maskImage(),
                                        linktype=scModel.getLinkType(frm,to))
            except Exception as e:
                print e
                print frm + ' to ' + to

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