# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import logging
from image_wrap import openImageFile,ImageWrapper
from video_tools import get_frame_rate
from graph_meta_tools import MetaDataExtractor
from software_loader import SoftwareLoader, getFileName
import numpy as np
from support import setPathValue ,getValue
import tool_set
import os
import traceback
import sys
import wrapt
"""
Support functions for auto-updating journals created with older versions of the tool"
"""

class ModelProxy(wrapt.ObjectProxy):

    def __init__(self, model):
        super(ModelProxy, self).__init__(model)
        self.done = set()

    def reproduceMask(self):
        who = (self.__wrapped__.start, self.__wrapped__.end)
        if who not in self.done:
            self.__wrapped__.reproduceMask()
            self.done.add(who)

def updateJournal(scModel):
    """
     Apply updates
     :param scModel: Opened project model
     :return: None. Updates JSON.
     @type scModel: ImageProjectModel
    """
    from collections import OrderedDict
    upgrades = scModel.getGraph().getDataItem('jt_upgrades')
    upgrades = upgrades if upgrades is not None else []
    gopLoader = scModel.gopLoader

    def apply_fix(fix, scModel, gopLoader, id):
        try:
            fix(scModel, gopLoader)
            return True
        except Exception as ex:
            logging.getLogger('maskgen').error('Failed to apply fix {} for version {}:{}'.format(
                fix.__name__, id, str(ex)
            ))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.getLogger('maskgen').error(
                ' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
            return False

    fixes = OrderedDict(
        [("0.3.1115", [_replace_oldops]),
         ("0.3.1213", [_fixQT]),
         ("0.4.0101.8593b8f323", [_fixResize, _fixResolution]),
         ("0.4.0101.b4561b475b", [_fixCreator, _fixValidationTime]),
         ("0.4.0308.f7d9a62a7e", [_fixLabels]),
         ("0.4.0308.f7d9a62a7e", [_fixPasteSpliceMask]),
         ("0.4.0308.90e0ce497f", [_fixTransformCrop]),
         ("0.4.0308.adee798679", [_fixEdgeFiles, _fixBlend]),
         ("0.4.0308.db2133eadc", [_fixFileArgs]),
         ("0.4.0425.d3bc2f59e1", [_operationsChange1]),
         ("04.0621.3a5c9635ef", [_fixProvenanceCategory]),
         ("04.0720.415b6a5cc4", [_fixRANSAC, _fixHP]),
         ("04.0720.b0ec584b4e", [_fixInsertionST]),
         ("04.0810.546e996a36", [_fixVideoAudioOps]),
         ("04.0810.9381e76724", [_fixCopyST, _fixCompression]),
         ("0.4.0901.723277630c", [_fixFrameRate, _fixRaws]),
         ("0.4.1115.32eabae8e6", [_fixRecordMasInComposite]),
         ("0.4.1204.5291b06e59", [_addColor, _fixAudioOutput, _fixEmptyMask, _fixGlobal]),
         ("0.4.1231.03ad63e6bb", [_fixSeams]),
         ("0.5.0227.c5eeafdb2e", [_addColor256, _fixDescriptions,_fixUserName]),
         ('0.5.0227.6d9889731b', [_fixPNGS,_emptyMask]),
         ("0.5.0227.db02ad8372", []),
         # it appears that bf007ef4cd went with 0227 and not 0401
         ('0.5.0227.bf007ef4cd', []),
         ('0.5.0401.bf007ef4cd', [_fixTool,_fixInputMasks]),
         ('0.5.0421.65e9a43cd3', [_fixContrastAndAddFlowPlugin,_fixVideoMaskType,_fixCompressor]),
         ('0.5.0515.afee2e2e08', [_fixOutputCGI]),
         ('0.5.0822.b3f4049a83', [_fixErasure, _fix_PosterizeTime_Op, _fixMetaStreamReferences, _repairNodeVideoStats, _fixTimeStrings, _fixDonorVideoMask]),
         ('0.5.0918.25f7a6f767', [_fix_Inpainting_SoftwareName]),
         ('0.5.0918.b370476d40', []),
         ('0.5.0918.b14aff2910', [_fixMetaDataDiff,_fixVideoNode,_fixSelectRegionAutoJournal, _fixNoSoftware, _fixVideoMasks]),
         ('0.5.0918.19c0afaab7', [_fixTool2]),
         ('0.5.1105.665737a167', []),
         ('0.5.1130.c118b19ba4', [_fixReplaceAudioOp, _fixSoftwareVersion]),
         ('0.5.1210.5ca3e81782', [_fixCAS]),
         ('0.6.0103.9d9b6e95f2', []),
         ('0.6.0117.76365a8b60', []),
         ('0.6.0208.ae6b74543d', []),
         ('0.6.0227.b469c4a202', [_fixAddCreateTime,_fixautopastecloneinputmask, _fixAudioDelete, _fixVideoMasksEndFrame])
         ])

    def _ConformVersion(version):
        if version.startswith('04'):
            return version.replace('04', '0.4', 1)
        else:
            return version

    versions= list(fixes.keys())
    # find the maximum match
    matched_versions = [versions.index(p) for p in upgrades if p in versions]
    project_version = scModel.getGraph().getProjectVersion()
    hasNodes = bool(scModel.G.get_nodes())
    isFrozen = scModel.G.isFrozen()
    if len(matched_versions) > 0:
        # fix what is left
        fixes_needed = max(matched_versions) - len(versions) + 1
    else:
        if not hasNodes or _ConformVersion(project_version) > versions[-1] or isFrozen:
            fixes_needed = 0
        elif project_version not in fixes:
            major_version = _ConformVersion(project_version)
            newest_match = next(version for version in versions if major_version <= _ConformVersion(version))
            fixes_needed = -(len(versions) - versions.index(newest_match))
        else:
            fixes_needed = -(len(versions) - versions.index(project_version)) if project_version in versions else -len(versions)
    ok = True
    stop_fix = None

    scModel = ModelProxy(scModel)
    if fixes_needed < 0:
        for id in fixes.keys()[fixes_needed:]:
            logging.getLogger('maskgen').info('Apply upgrade {}'.format(id))
            for fix in fixes[id]:
                logging.getLogger('maskgen').info('Apply fix {} for {}'.format(fix.__name__, id))
                ok &= apply_fix(fix, scModel, gopLoader, id)
                if ok:
                    stop_fix = fix

    apply_fix(_fixMandatory, scModel, gopLoader,fixes.keys()[-1])
    if isFrozen:
        logging.getLogger('maskgen').info('This Journal has been FROZEN. '
                                          'It does contain probes, but the journal cannot be updated. '
                                          'This is usually due to files missing from the journal archive.')
    #update to the max
    upgrades = fixes.keys()[-1:] if ok else [stop_fix]
    if scModel.getGraph().getVersion() not in upgrades and ok:
        upgrades.append(scModel.getGraph().getVersion())
    scModel.getGraph().setDataItem('jt_upgrades',upgrades,excludeUpdate=True)
    return ok

def _fixautopastecloneinputmask(scModel, gopLoader):
     if scModel.getGraph().getDataItem('autopastecloneinputmask') is None:
        scModel.getGraph().setDataItem('autopastecloneinputmask', 'no')

def _fixAudioDelete(scModel, gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op = gopLoader.getOperationWithGroups(edge['op'], fake=True, warning=False)
        if op.category in 'Audio' and op.name not in ['AudioSample']:
            try:
                if 'videomasks' in edge:
                    edge.pop('videomasks')
                scModel.select((frm, to))
                scModel.reproduceMask()
            except Exception as e:
                logging.getLogger('maskgen').warning(
                    'Could not correct video masks {}->{}: {}'.format(frm, to, e.message))

def _fixAddCreateTime(scModel, gopLoader):
    times = []
    for node_id in scModel.G.get_nodes():
        node = scModel.G.get_node(node_id)
        ctime = getValue(node,'ctime')
        if ctime is not None:
            times.append(ctime)
    times = sorted(times)
    scModel.G.setDataItem('createtime',times[0])

def _fixReplaceAudioOp(scModel, gopLoader):
    """
    Replaces the ReplaceAudioSample operation with AddAudioSample Operation,
    Setting the 'add type' argument to 'replace'
    :param scModel:
    :param gopLoader:
    :return:
    """
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op_name = getValue(edge, 'op', '')
        if op_name == 'ReplaceAudioSample':
            edge['op'] = 'AddAudioSample'
            setPathValue(edge, 'arguments.add type', 'replace')
            setPathValue(edge, 'arguments.synchronization', 'none')
            setPathValue(edge, 'arguments.Direct from PC', 'no')

def _fixCAS(scModel, gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op_name = getValue(edge, 'op', '')
        if op_name == 'TransformContentAwareScale':
            node = scModel.G.get_node(frm)
            if getValue(node, 'filetype', 'image') == 'video':
                edge['op'] = 'PasteSampled'
            else:
                edge['op'] = 'TransformSeamCarving'
                setPathValue(edge,'arguments.inputmasktype','keep')
                setPathValue(edge, 'arguments.apply mask', 'yes')
        if op_name == 'ContentAwareFill':
            node = scModel.G.get_node(frm)
            if getValue(node, 'filetype', 'image') == 'video':
                edge['op'] = 'PasteSampled'
        if op_name == 'TransformSeamCarving':
            setPathValue(edge, 'arguments.inputmasktype', 'color')
            setPathValue(edge, 'arguments.apply mask', 'no')
        # should have been fixed a while ago
        if op_name == 'OutputPng':
            if getValue(edge,'arguments.Lens Distortion Applied','') == '':
                setPathValue(edge, 'arguments.Lens Distortion Applied', 'no')

def _fixNoSoftware(scModel, gopLoader):
    """
    fills in missing softwareName field.
    :param scModel:
    :param gopLoader:
    :return:
    """
    from collections import Counter

    used_software = []
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op_name = getValue(edge, 'op', '')
        if op_name == 'Recapture':
            setPathValue(edge, 'softwareName', 'Off Camera')
        software_name = getValue(edge, 'softwareName', '')
        if software_name != '' and software_name.lower() != 'no software':
            used_software.append(software_name)

    #use most commonly used software in the Journal if Empty
    counter = Counter(used_software)
    if len(counter) == 0:
        return
    most_used_software = counter.most_common(1)[0][0]
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op_name = getValue(edge, 'op', '')
        software_name = getValue(edge, 'softwareName', '')
        if (software_name == '' or software_name.lower() == 'no software') and op_name != 'Donor':
            setPathValue(edge, 'softwareName', most_used_software)

def _fix_Inpainting_SoftwareName(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'PasteSampled' \
                and getValue(edge, 'tool', '') == 'PostInpaint.py' \
                and getValue(edge, 'softwareName', '') == '':
            edge['softwareName'] = 'UoMInPainting'
            edge['softwareVersion'] = '2.8'

def _fixSoftwareVersion(scModel, gopLoader):

    sl = SoftwareLoader()

    adobe = {"14.1": "CC 2014", "14.2": "CC 2014", "15.0": "CC 2014", "15.2": "CC 2014", "16.0": "CC 2015",
             "16.1": "CC 2015", "16.2": "CC 2015", "16.16": "CC 2015",
             "17.0": "CC 2015", "18.0": "CC 2017", "18.1": "CC 2017", "19.0": "CC 2018", "20.0": "CC 2019",
             "2014": "CC 2014", "2015": "CC 2015", "2016": "CC 2016", "2017": "CC 2017", "2018": "CC 2018",
             "2019": "CC 2019"}

    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        softwareName = getValue(edge, 'softwareName','')
        softwareVersion = getValue(edge, 'softwareVersion','').strip()
        versions = sl.get_versions(softwareName)
        if len(versions) == 0:
            #if the software is not in the jt and is one digit/char make it x.0
            if len(softwareVersion) == 1:
                softwareVersion = softwareVersion + ".0"
        else:
            #software is in the jt
            modified = False
            #if one of the versions in the jt is in the software version use the jt version
            for v in versions:
                v = v.strip()
                if v in softwareVersion or v.lower() in softwareVersion.lower():
                    softwareVersion = v
                    modified = True
            if not modified:
                if 'adobe' in softwareName.lower():
                    for key in adobe:
                        if key in softwareVersion:
                            softwareVersion = adobe[key]
                            break
        edge['softwareVersion'] = softwareVersion


def _fixSelectRegionAutoJournal(scModel, gopLoader):

    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        plugin_name = getValue(edge, 'plugin_name', '')
        if plugin_name == 'SelectRegion':
            setPathValue(edge, 'arguments.subject', 'other')

    donor_base_tuples = scModel.getDonorAndBaseNodeTuples()
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        plugin_name = getValue(edge, 'plugin_name', '')
        if plugin_name == 'PasteSplice':
            for db_tuple in donor_base_tuples:
                if to == db_tuple[0][1]:
                    for idx in range(0, len(db_tuple[2])-1):
                        to_node = db_tuple[2][idx]
                        frm_node = db_tuple[2][idx+1]
                        node_edge = scModel.G.get_edge(frm_node, to_node)
                        if getValue(node_edge, 'op', '') == 'SelectRegion':
                            setPathValue(edge, 'arguments.subject', getValue(node_edge, 'arguments.subject', 'other'))
                            break
            setPathValue(edge, 'arguments.purpose', 'add')


def _fix_PosterizeTime_Op(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'TimeAlterationPosterizeTime':
            edge['op'] = 'TimeAlterationFrameRate'

def _fixVideoNode(scModel, gopLoader):
    from scenario_model import VideoAddTool
    from ffmpeg_api import get_stream_indices_of_type, is_vfr
    tool = VideoAddTool()
    def needs_rerun(meta):
        indices = get_stream_indices_of_type(meta, 'video')
        if indices:
            return True
        return False
    for node_id in scModel.G.get_nodes():
        node = scModel.G.get_node(node_id)
        if getValue(node,'filetype','image') == 'video' and \
                (getValue(node, 'media', None) is None or
                  needs_rerun(getValue(node, 'media', []))):
            logging.getLogger('maskgen').info('load data for {}'.format(scModel.G.get_pathname(node_id)))
            node.update(tool.getAdditionalMetaData(scModel.G.get_pathname(node_id)))

def _fixDonorVideoMask(scModel, gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'Donor' and \
            scModel.getNodeFileType(frm) == 'video' and \
            scModel.getNodeFileType(to) == 'video':
            scModel.select((frm,to))
            scModel.reproduceMask()

def _fixMandatory(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        frm_file = scModel.G.get_pathname(frm)
        frm_file_type = tool_set.fileType(frm_file)
        args = getValue(edge,'arguments',{})
        op = gopLoader.getOperationWithGroups(edge['op'],fake=True, warning=False)
        missing = [param for param in op.mandatoryparameters.keys() if
                   (param not in args or len(str(args[param])) == 0) and \
                   ('source' not in op.mandatoryparameters[param] or op.mandatoryparameters[param][
                       'source'] == frm_file_type)]
        for missing_name in missing:
            dv =  getValue(op.mandatoryparameters[missing_name],'defaultvalue',None)
            if dv is not None:
                args[missing_name] = dv
        if len(args) > 0:
            edge['arguments'] = args

def _fixRawFilter(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if getValue(edge,'op','') == 'CameraRawFilter':
            edge['op'] = 'CreativeFilter'

def _fixMetaStreamReferences(scModel, gopLoader):
    from re import search

    def videoStreamDoesExist(nodeMeta):
        from ffmpeg_api import get_stream_indices_of_type, get_meta_from_video
        filepath = os.path.abspath(os.path.join(scModel.G.dir, nodeMeta['file']))
        if os.path.exists(filepath):
            meta, frames = get_meta_from_video(filepath, show_streams=True, with_frames=False, media_types=['audio', 'video'])
            videoIndexes = get_stream_indices_of_type(meta, 'video')
            return bool(videoIndexes)
        else:
            if 'codec_type' in nodeMeta:
                return nodeMeta['codec_type'] == 'video'
            else:
                return getValue(nodeMeta,'filetype','video') == 'video'

    def remap(stream, hasvideo = True):
        index_map = {'0':'video', '1':'mono'} if hasvideo else {'0':'mono'}
        for meta_key in stream.keys():
            #safety if we already did this one from before.
            if not 'video:' in meta_key or not 'mono:' in meta_key:
                lookup = replace = ''
                if meta_key[0].isdigit():  # handle first character being the lookup key
                    lookup = replace = meta_key[0]
                else:
                    match = search(r"(#\d:\d)", meta_key)  #handle #0:0 pattern
                    if match != None:
                        lookup = match.group(0)[-1]
                        replace = match.group(0) + '.' if match.start() == 0 else meta_key #replace #0:0. or whole key

                if lookup in index_map:
                    id = index_map[lookup]
                elif lookup != '':  #add unknown lookup keys, assume audio.
                    id = 'mono'
                    tally = len([mapping for mapping in index_map.values() if id in mapping])
                    if tally > 0:
                        id = id + str(tally)
                    index_map[lookup] = id
                else:
                    id = index_map['0'] #if no lookup key present, assume 0

                if replace == meta_key or '.' in replace: #add colon separator if need be
                    id = id + ':'

                new_meta_key = meta_key.replace(replace, id) if replace != '' else id + ':' + meta_key
                stream[new_meta_key] = stream.pop(meta_key)

    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        frm_node = scModel.G.get_node(frm)
        to_node = scModel.G.get_node(to)
        metadiff = getValue(edge,'metadatadiff')
        if metadiff is not None and type(metadiff) != list:
            hasvideo = [videoStreamDoesExist(frm_node), videoStreamDoesExist(to_node)]
            remap(metadiff, hasvideo=hasvideo[1])
            edge['metadatadiff'] = metadiff
        

def _fixMetaDataDiff(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        metadiff = getValue(edge,'metadatadiff')
        if metadiff is not None:
            if type(metadiff) == list:
                md = {}
                edge['metadatadiff'] = md
                if len(metadiff) > 0:
                    for k,v in metadiff[0].iteritems():
                        parts = k.split(':')
                        if len(parts) > 1:
                            if parts[0] not in md:
                                md[parts[0]]  = {}
                            md[parts[0]][parts[1]] = v



def _fixInputMasks(scModel,gopLoader):
    scModel.fixInputMasks()

def _fixPNGS(scModel,gopLoader):
    """

    :param scModel:
    :param gopLoader:
    :return:
    @type scModel: ImageProjectModel
    """
    import glob
    import imghdr
    for png_file in glob.glob(os.path.join(os.path.abspath(scModel.get_dir()) , '*.png')):
        if imghdr.what(png_file) == 'tiff':
            openImageFile(png_file).save(png_file,format='PNG')

def _repairNodeVideoStats(scModel,gopLoader):
    """
      USed to correct the use of the third ':' which indicated frames since time.
      This caused confusion.  Users often used the the third ':' for milliseconds.
      The journals are of course incorrect.  Cannot fix that here.
      :param scModel:
      :param gopLoader:
      :return:
      @type scModel: ImageProjectModel
      """
    import re
    cross_attributes = ['codec_name','codec_tag','codec_long_name','codec_type',
                        'codec_tag_string','profile','duration_ts','duration'
                        'nb_frames']
    video_attributes = ['avg_frame_rate','r_frame_rate','codec_time_base',
                        'coded_width','coded_height','has_b_frames','sample_aspect_ratio',
                        'display_aspect_ratio','color_space','timecode','is_avc',
                        'start_pts','start_time','duration','duration_ts','pix_fmt',
                        'width','height','nal_length_size','time_base','chroma_location']
    audio_attributes = ['sample_rate','channels','channel_layout',
                        'sample_fmt']
    attributes_to_drop = ['index','id',
                          'start_time',
                          'bit_rate',
                          'max_bit_rate',
                          'bits_per_sample',
                          'bits_per_raw_sample',
                          'nb_read_frames',
                          'nb_read_packets',
                          re.compile('DISPOSITION:.*'),
                          re.compile('TAG:.*'),
                          'level',
                          'color_range',
                          'color_transfer',
                          'color_primaries',
                          'refs',
                          'field_order',
                          re.compile('.*SIDE_DATA.*'),
                          re.compile('000.*:.*'),
                          'displaymatrix']

    def match_name_or_key(att_name_or_re,item_key):
        is_not_re = type(att_name_or_re) in [str, unicode]
        return (is_not_re and att_name_or_re == item_key) or \
               (not is_not_re and att_name_or_re.match(item_key) is not None)

    for node_id in scModel.getGraph().get_nodes():
        node = scModel.getGraph().get_node(node_id)
        codec_type = getValue(node, 'codec_type','video')
        media = {}
        for item_key in node.keys():
            for att_name_or_re in attributes_to_drop:
                if match_name_or_key(att_name_or_re,item_key):
                        node.pop(item_key)
            if 'audio' in media:
                for att_name_or_re in audio_attributes:
                    if match_name_or_key(att_name_or_re, item_key):
                        media['audio'][item_key] = node.pop(item_key)
            if 'video' in media:
                for att_name_or_re in video_attributes:
                    if match_name_or_key(att_name_or_re, item_key):
                        media['video'][item_key] = node.pop(item_key)
            for att_name_or_re in cross_attributes:
                if match_name_or_key(att_name_or_re, item_key):
                    if codec_type in media:
                        media[codec_type][item_key] = node.pop(item_key)
        if len(media) > 0:
            node['media'] = media


def _fixTimeStrings(scModel, gopLoader):
    """
    USed to correct the use of the third ':' which indicated frames since time.
    This caused confusion.  Users often used the the third ':' for milliseconds.
    The journals are of course incorrect.  Cannot fix that here.
    :param scModel:
    :param gopLoader:
    :return:
    """
    from tool_set import getMilliSecondsAndFrameCount,getDurationStringFromMilliseconds
    extractor = MetaDataExtractor(scModel.getGraph())
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        args = getValue(edge,'arguments',{})
        try:
            for k,v in args.iteritems():
                if 'Time' in k and  v.count(':') == 3:
                    m,f = getMilliSecondsAndFrameCount(v)
                    rate = get_frame_rate(extractor.getMetaDataLocator(frm))
                    if rate is not None:
                        m += int(f*1000.0/rate)
                    v = getDurationStringFromMilliseconds(m)
                    setPathValue(edge,'arguments.{}'.format(k),v)
        except:
            pass

def _fixErasure(scModel, gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if getValue(edge,'op','') == 'ErasureByGAN':
            if getValue(edge,'arguments.model','') == 'resize_GAN_model.npz':
                edge['op'] = 'ErasureByGAN::Resize'
            else:
                edge['op'] = 'ErasureByGAN::Multi'

def _emptyMask(scModel, gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'videomasks' in edge:
            continue
        if 'maskname' in edge:
            mask = scModel.G.get_edge_image(frm,to, 'maskname')
            if mask is not None and np.all(mask.to_array() == 255):
                edge['empty mask'] = 'yes'

def _fixTool(scModel,gopLoader):
    """
    :param scModel:
    :param gopLoader:
    :return:
    @type scModel: ImageProjectModel
    """
    summary = scModel.getProjectData('technicalsummary',
                                     default_value=scModel.getProjectData('technicalSummary',default_value=''))
    if len(summary) > 0:
        scModel.setProjectData('technicalsummary',summary)
    description = scModel.getProjectData('projectdescription',
                                         default_value=scModel.getProjectData('projectDescription'))
    if description is not None:
        scModel.setProjectData('projectdescription', description)
    tool_name = 'jtui'
    creator = scModel.getGraph().getDataItem('creator')
    if summary.lower().startswith('automate') or creator in ['alice', 'dupre']:
        tool_name = 'jtproject'
    modifier_tools = [tool_name]
    # no easy way to find extensions, since all extensions are plugins
    modified_users = set()
    for frm, to in scModel.getGraph().get_edges():
        edge = scModel.G.get_edge(frm, to)
        user = getValue(edge,'username',defaultValue='x')
        if user in ['alice', 'saffire', 'dupre'] and getValue(edge,'automated', defaultValue='no') == 'yes':
            modified_users.add(user)
    if len(modified_users) > 2 or creator not in modified_users:
        modifier_tools.append('jtprocess')

    if scModel.getGraph().getDataItem('modifier_tools') is None:
        scModel.getGraph().setDataItem('modifier_tools', modifier_tools)

    scModel.getGraph().setDataItem('creator_tool', tool_name)

def _fixTool2(scModel,gopLoader):
    """

    :param scModel:
    :param gopLoader:
    :return:
    @type scModel: ImageProjectModel
    """

    def replace_tool(tool):
        return 'jtui' if 'MaskGenUI' in tool else tool

    modifier_tools = scModel.getGraph().getDataItem('modifier_tools')
    if modifier_tools is not None:
        scModel.getGraph().setDataItem('modifier_tools', [replace_tool(x) for x in modifier_tools])

    creator_tool= scModel.getGraph().getDataItem('creator_tool')
    scModel.getGraph().setDataItem('creator_tool', replace_tool(creator_tool))

def _fixValidationTime(scModel,gopLoader):
    import time
    validationdate = scModel.getProjectData('validationdate')
    if validationdate is not None and len(validationdate) > 0:
        scModel.setProjectData('validationtime',time.strftime("%H:%M:%S"),excludeUpdate=True)

def _fixProvenanceCategory(scModel,gopLoader):
    from maskgen.graph_rules import  manipulationCategoryRule
    cat = scModel.getProjectData('manipulationcategory',default_value='')
    if cat is not None and cat.lower() == 'provenance':
        scModel.setProjectData('provenance','yes')
    else:
        scModel.setProjectData('provenance', 'no')
    scModel.setProjectData('manipulationcategory',manipulationCategoryRule(scModel,None))

def _updateEdgeHomography(edge):
    if 'RANSAC' in edge:
        value = edge.pop('RANSAC')
        if value == 'None' or value == 0 or value == '0':
            edge['homography'] = 'None'
        else:
            edge['homography'] = 'RANSAC-' + str(value)
        if 'Transform Selection' in edge and edge['Transform Selection'] == 'Skip':
            edge['homography'] = 'None'
        if 'sift_max_matches' in edge:
            edge['homography max matches'] = edge.pop('sift_max_matches')

def _addColor(scModel,gopLoader):
    scModel.assignColors()

def _addColor256(scModel, gopLoader):
    if len(scModel.getGraph().get_edges())>=256:
        scModel.assignColors()

def _fixHP(scModel,gopLoader):
    for nodename in scModel.getNodeNames():
        node= scModel.G.get_node(nodename)
        if 'HP' in node:
            node['Registered'] = node.pop('HP')

def _fixCompressor(scModel,gopLoader):
    for nodename in scModel.getNodeNames():
        node = scModel.G.get_node(nodename)
        file = getValue(node,'file','')
        if file[:-4].endswith('_compressed'):
            node['compressed'] = u'maskgen.video_tools.x264fast'

def _fixOutputCGI(scModel, gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'ObjectCGI':
            inputmask = getValue(edge,'inputmaskname')
            if inputmask is not None:
                setPathValue(edge,'arguments.model image',inputmask)
                edge.pop('inputmaskname')
                scModel.G.addEdgeFilePath('arguments.model image','')

def _fixVideoMasksEndFrame(scModel, gopLoader):
    from maskgen import video_tools
    extractor = MetaDataExtractor(scModel.getGraph())
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        masks = edge['videomasks'] if 'videomasks' in edge else []
        reproduction = False
        for mask in masks:
            if mask['type'] in ['video','audio']:
                end_time = getValue(edge, 'arguments.End Time')
                result = video_tools.getMaskSetForEntireVideo(extractor.getMetaDataLocator(frm),media_types=[mask['type']]) \
                        if os.path.exists(scModel.G.get_pathname(frm)) else None
                result = result[0] if result is not None and len(result) > 0 else None
                if (result is None or 'endframe' not in result) and end_time is None:
                    rate = float(video_tools.get_rate_from_segment(mask))
                    mask['error'] = getValue(mask,'error',0) + 2*float(1000.0/rate)
                    continue
                diff = result['endframe'] - mask['endframe']
                if diff > 0 and end_time is None:
                    mask['endtime'] = result['endtime']
                    mask['endframe'] = result['endframe']
                    mask['frames'] = mask['endframe'] - mask['startframe'] + 1
                else:
                    reproduction = diff < 0
        if reproduction:
            scModel.select((frm,to))
            try:
                scModel.reproduceMask()
            except Exception as e:
                logging.getLogger('maskgen').warning(
                    'Could not correct {} masks {}->{}: {}'.format(mask['type'], frm, to, e.message))


def _fixVideoMaskType(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        masks = edge['videomasks'] if 'videomasks' in edge else []
        for mask in masks:
            if 'type' not in mask:
                mask['type'] = 'audio' if 'Audio' in edge['op'] else 'video'

def _fixFrameRate(scModel,gopLoader):
    from maskgen import video_tools
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        masks = edge['videomasks'] if 'videomasks' in edge else []
        for mask in masks:
            if 'rate' in mask:
                if type(mask['rate']) == list:
                    mask['rate'] = float(mask['rate'][0])
                elif mask['rate']<0:
                    mask['rate'] = float(mask['rate'])*1000.0
            else:
                mask['rate'] = video_tools.get_rate_from_segment(mask)
            if 'startframe' not in mask:
                mask['startframe'] = video_tools.get_start_frame_from_segment(mask)
            if 'endframe' not in mask:
                mask['endframe'] = video_tools.get_end_frame_from_segment(mask)
            if 'starttime' not in mask:
                mask['starttime'] = video_tools.get_start_time_from_segment(mask)
            if 'endtime' not in mask:
                mask['endtime'] = video_tools.get_end_time_from_segment(mask)
            if 'frames' not in mask:
                mask['frames'] = video_tools.get_frames_from_segment(mask)
            if 'type' not in mask:
                mask['type'] = 'audio' if 'Audio' in edge['op'] else 'video'

def _fixRANSAC(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        args = edge['arguments'] if 'arguments' in edge else dict()
        _updateEdgeHomography(edge)
        _updateEdgeHomography(args)
        if edge['op'] == 'Donor':
            edge['homography max matches'] = 20

def _fixVideoMasks(scModel, gopLoader):
    def contains_files(edge):
        return len([m for m in getValue(edge, 'videomasks', []) if getValue(m,'videosegment','') != '']) > 0
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'videomasks' in edge and (contains_files(edge) or len(getValue(edge, 'videomasks', [])) == 0):
            try:
                edge.pop('videomasks')
                scModel.select((frm, to))
                scModel.reproduceMask()
            except Exception as e:
                logging.getLogger('maskgen').warning('Could not correct video masks {}->{}: {}'.format(frm,to,e.message))

def _fixRaws(scModel,gopLoader):
    if scModel.G.get_project_type()!= 'image':
        return
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in [ 'OutputPng', 'Recapture'] and \
             'shape change' in edge and tool_set.toIntTuple(edge['shape change']) != (0,0):
            node = scModel.G.get_node(frm)
            file = os.path.join(scModel.get_dir(), node['file'])
            redo =  tool_set.fileType(file) == 'image' and \
                file.lower()[-3:] not in ['iff','tif','png','peg','jpeg','gif','pdf','bmp']
            node = scModel.G.get_node(to)
            file = os.path.join(scModel.get_dir(),node['file'])
            redo |= tool_set.fileType(file) == 'image' and \
                file.lower()[-3:] not in ['iff','tif','png','peg','jpeg','gif','pdf','bmp']
            if redo:
                scModel.select((frm,to))
                scModel.reproduceMask()

def _fixSeams(scModel,gopLoader):
    if scModel.G.get_project_type()!= 'image':
        return
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in [ 'TransformSeamCarving'] and edge['softwareName'] == 'maskgen':
            bounds = getValue(edge,'arguments.percentage bounds')
            if  bounds is not None:
                edge['arguments'].pop('percentage bounds')
                edge['arguments']['percentage_width'] = float(bounds)/100.0
                edge['arguments']['percentage_height'] = float(bounds)/100.0
            keep  = getValue(edge, 'arguments.keepSize')
            if keep is not None:
                edge['arguments']['keep'] = 'yes' if keep == 'no' else 'no'
            mask =  getValue(edge,'inputmaskname')
            if mask is not None:
                try:
                    im = openImageFile(os.path.join(scModel.get_dir(),mask))
                    if im is not None:
                        oldmask = im.to_array()
                        newmask = np.zeros(oldmask.shape,dtype=np.uint8)
                        newmask[:,:,1] = oldmask[:,:,0]
                        newmask[:,:,0] = oldmask[:,:,1]
                        ImageWrapper(newmask).save(os.path.join(scModel.get_dir(),mask))
                except Exception as e:
                    logging.getLogger('maskgen').error('Seam Carve fix {} mask error {}'.format(mask,str(e)))

def _fixVideoAudioOps(scModel,gopLoader):
    groups = scModel.G.getDataItem('groups')
    if groups is None:
        groups = {}
    op_mapping = {
        'AudioPan':'AudioAmplify',
        'SelectFromFrames':'SelectRegionFromFrames',
        'ColorInterpolation':'ColorLUT',
        'SelectRemoveFromFrames':'ContentAwareFill'
    }
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] in groups:
            ops = groups[edge['op']]
        else:
            ops = [edge['op']]
        for op in ops:
            if op in op_mapping:
                args = edge['arguments'] if 'arguments' in edge else dict()
                if len(ops) == 1:
                    edge['op'] = op_mapping[op]
                if 'chroma key insertion' in args:
                    args['key insertion'] = args.pop('chroma key insertion')
                if 'Left' in args:
                    args['Left Pan'] = args.pop('Left')
                if 'Right' in args:
                    args['Right Pan'] = args.pop('Right')
                if edge['op'] == 'ContentAwareFill':
                    args['purpose'] = 'remove'
    newgroups = {}
    for k, v in groups.iteritems():
        newgroups[k] = [op_mapping[op] if op in op_mapping else op for op in v]
    scModel.G.setDataItem('groups', newgroups)

def _fixInsertionST(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        args = edge['arguments'] if 'arguments' in edge else dict()
        if 'Insertion Start Time' in args:
            args['Start Time'] = args.pop('Insertion Start Time')
        if 'Insertion End Time' in args:
            args['End Time'] = args.pop('Insertion End Time')

def _fixCompression(scModel,gopLoader):
    for nname in scModel.G.get_nodes():
        node = scModel.G.get_node(nname)
        if node['file'].endswith('_compressed.avi'):
            node['compressed'] = 'maskgen.video_tools.x264'

def _fixCopyST(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        args = edge['arguments'] if 'arguments' in edge else dict()
        if 'Copy Start Time' in args:
            args['Start Time'] = args.pop('Copy Start Time')
        if 'Copy End Time' in args:
            args['End Time'] = args.pop('Copy End Time')

def _operationsChange1(scModel,gopLoader):
    projecttype = scModel.G.getDataItem('projecttype')
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
        'ArtifactsCGIArtificialLighting':'ArtificialLighting',
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
        'ColorOpacity': 'LayerOpacity',
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
            elif op in op_mapping and len(ops) == 1:
                edge['op'] = op_mapping[op]
        newgroups = {}
        for k,v in groups.iteritems():
            newgroups[k] = [op_mapping[op] if op in op_mapping else op for op in v]
        scModel.G.setDataItem('groups', newgroups)

def _pasteSpliceBlend(scModel,gopLoader):
    import copy
    from group_filter import GroupFilterLoader
    gfl = GroupFilterLoader()
    scModel.G.addEdgeFilePath('arguments.Final Image', 'inputmaskownership')
    grp = gfl.getGroup('PasteSpliceBlend')
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
            mod = scModel.getModificationForEdge(frm, to)
            scModel.imageFromGroup(grp, software=mod.software, **args)

def _fixColors(scModel,gopLoader):
    scModel.assignColors(scModel)

def _fixLabels(scModel,gopLoader):
    for node in scModel.getNodeNames():
        scModel.labelNodes(node)

def _fixFileArgs(scModel,gopLoader):
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
    scModel.G.addNodeFilePath('KML File', '')

def _fixEdgeFiles(scModel,gopLoader):
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

def _fixCreator(scModel,gopLoader):
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    modifications = sorted(scModel.getDescriptions(), key=lambda mod: mod.ctime, reverse=False)
    if len(modifications) > 0:
       scModel.getGraph().setDataItem('creator',modifications[0].username,excludeUpdate=True)

def _fixLocalRotate(scModel,gopLoader):
    """

    :param scModel:
    :param gopLoader:
    :return:
    @type scModel: ImageProjectModel
    """
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'].lower() == 'transformrotate':
            tm = edge['transform matrix'] if 'transform matrix' in edge  else None
            sizeChange = tool_set.toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
            local = 'yes' if  tm is not None and sizeChange == (0, 0) else 'no'
            if 'arguments' not in edge:
                edge['arguments'] = {'local' : local}
            else:
                edge['arguments']['local']  = local
            if tm is None and  sizeChange == (0,0):
                if 'arguments' in edge and 'homography' in edge['arguments']:
                    edge['arguments'].pop('homography')
                scModel.reproduceMask(edge_id=(frm, to))

def _fixBlend(scModel,gopLoader):
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

def _fixTransformCrop(scModel,gopLoader):
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

def _fixResolution(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'arguments' in edge and 'scale'  in edge['arguments']:
            if type( edge['arguments']['scale']) != float:
                edge['arguments']['resolution'] = edge['arguments']['scale'].replace(':','x')

def _fixResize(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if edge['op'] == 'TransformResize':
            if 'arguments' not in edge:
                edge['arguments'] = {}
            if 'interpolation' not in edge['arguments']:
                edge['arguments']['interpolation']  = 'other'

def _fixPasteSpliceMask(scModel,gopLoader):
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


def _fixUserName(scModel,gopLoader):
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    from maskgen import software_loader
    names = software_loader.getFileName('ManipulatorCodeNames.txt')
    if names is None:
        logging.getLogger('maskgen').warn('Can not repair user names; ManipulatorCodeNames.txt is missing.')
        return
    with open(names,'r') as f:
        allnames = [x.strip() for x in f.readlines()]

    def levenshtein(s, t):
        ''' From Wikipedia article; Iterative with two matrix rows. '''
        if s == t:
            return 0
        elif len(s) == 0:
            return len(t)
        elif len(t) == 0:
            return len(s)
        v0 = [None] * (len(t) + 1)
        v1 = [None] * (len(t) + 1)
        for i in range(len(v0)):
            v0[i] = i
        for i in range(len(s)):
            v1[0] = i + 1
            for j in range(len(t)):
                cost = 0 if s[i] == t[j] else 1
                v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
            for j in range(len(v0)):
                v0[j] = v1[j]
        return v1[len(t)]

    def best_name(oldname):
        if oldname not in allnames and len(allnames) > 0:
            try:
                alldistances = [levenshtein(oldname,x) for x in allnames]
                oldname = allnames[np.argmin(alldistances)]
            except:
                oldname = allnames[0]
        return oldname

    if scModel.getGraph().getDataItem('username') is not None:
        scModel.getGraph().setDataItem('username',best_name(scModel.getGraph().getDataItem('username').lower()))
    if scModel.getGraph().getDataItem('creator') is not None:
        scModel.getGraph().setDataItem('creator', best_name(scModel.getGraph().getDataItem('creator').lower()))
    for frm, to in scModel.getGraph().get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'username' in edge:
            edge['username']  = best_name(edge['username'])

def _fixQT(scModel,gopLoader):
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

def _fixTransforms(scModel,gopLoader):
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

def _fixRecordMasInComposite(scModel,gopLoader):
    """
    Replace true value with  'yes'
    :param scModel: Opened project model
    :return: None. Updates JSON.
    @type scModel: ImageProjectModel
    @type gopLoader: GroupOperationsLoader
    """
    for frm, to in scModel.G.get_edges():
         edge = scModel.G.get_edge(frm, to)
         if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'true':
            edge['recordMaskInComposite'] = 'yes'
         op = gopLoader.getOperationWithGroups(edge['op'],fake=True, warning=False)
         if op.category in ['Output','AntiForensic','Laundering']:
             edge['recordMaskInComposite'] = 'no'

def _fixGlobal(scModel,gopLoader):
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        op = gopLoader.getOperationWithGroups(edge['op'],fake=True, warning=False)
        if 'global' in edge and edge['global'] == 'yes' and "maskgen.tool_set.localTransformAnalysis" in op.analysisOperations:
            edge['global'] = 'no'

def _fixEmptyMask(scModel,gopLoader):
    import numpy as np
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        if 'empty mask' not in edge and ('recordInCompositeMask' not in edge or edge['recordInCompositeMask'] == 'no') \
                and  'videomasks' not in edge:
            mask = scModel.G.get_edge_image(frm,to, 'maskname', returnNoneOnMissing=True)
            edge['empty mask'] = 'yes' if mask is None or np.all(mask == 255) else 'no'

def _fixAudioOutput(scModel,gopLoader):
    """
     Consolidate Audio Outputs
    :param scModel: Opened project model
    :return: None. Updates JSON.
    @type scModel: ImageProjectModel
    @type gopLoader: GroupOperationsLoader
    """
    for frm, to in scModel.G.get_edges():
         edge = scModel.G.get_edge(frm, to)
         if edge['op'] in ['OutputAIF','OutputWAV']:
             edge['op'] = 'OutputAudioPCM'
         elif edge['op'] in ['OutputM4']:
             edge['op'] = 'OutputAudioCompressed'
         if 'Start Time' in edge and edge['Start Time'] == '0':
             edge['Start Time'] = '00:00:00'


def _fixSeam(scModel,gopLoader):
    """
   Seam Carving is recorded in Composite
    :param scModel: Opened project model
    :return: None. Updates JSON.
    @type scModel: ImageProjectModel
    @type gopLoader: GroupOperationsLoader
    """
    for frm, to in scModel.G.get_edges():
         edge = scModel.G.get_edge(frm, to)
         if edge['op'] == 'TransformSeamCarving':
             edge['recordMaskInComposite'] = 'yes'


def _replace_oldops(scModel,gopLoader):
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
            currentLink['recordMaskInComposite'] = 'yes'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            currentLink['arguments']['purpose'] = 'heal'


def _fixContrastAndAddFlowPlugin(scModel, gopLoader):
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        oldOp = currentLink['op']
        if oldOp == 'ColorBalance' and getValue(currentLink,'plugin_name') == 'Contrast':
            currentLink['op'] = 'Contrast'
        if oldOp == 'TimeAlterationWarp' and getValue(currentLink,'plugin_name') == 'FlowDrivenVideoTimeWarp':
            startTime = getValue(currentLink,'arguments.Start Time')
            count = getValue(currentLink,'arguments.Frames to Add')
            setPathValue(currentLink,'arguments.End Time', str(int(startTime) + int(count) - 1))

def _fixDescriptions(scModel, gopLoader):
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        if 'plugin_name' not in currentLink:
            continue
        plugin_name  = currentLink['plugin_name']
        if plugin_name == 'GammaCollection':
            setPathValue(currentLink,'arguments.selection type', 'auto')
        elif plugin_name == 'MajickConstrastStretch':
            setPathValue(currentLink,'arguments.selection type', 'NA')
        elif plugin_name == 'MajickEqualization':
            setPathValue(currentLink, 'arguments.selection type', 'NA')
            setPathValue(currentLink,'description',plugin_name + ': Equalize histogram: https://www.imagemagick.org/Usage/color_mods/#equalize.')
        elif plugin_name == 'GaussianBlur' and getValue(currentLink,'arguments.Laundering') is not None:
            setPathValue(currentLink, 'arguments.Laundering', 'no')
        elif plugin_name == 'ManualGammaCorrection':
            setPathValue(currentLink, 'arguments.selection type', 'manual')
            setPathValue(currentLink, 'description',
                                  plugin_name + ': Level gamma adjustment  (https://www.imagemagick.org/script/command-line-options.php#gamma)')

