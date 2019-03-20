# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import os
from maskgen.scenario_model import ImageProjectModel, MaskgenThreadPool, prefLoader
from maskgen.tool_set import *
from maskgen.video_tools import get_file_from_segment
import tarfile
import csv
from maskgen.mask_rules import *


"""
Support Functions for the Probe Generation Services
"""


def append_segment(row, segment):
    """
    Given a row of the CSV, append the video segment information

    Return the the segment to the row with appended segment
    :param row: list
    :param segment: VideoSegment
    :return: file name for segment
    @type row: list
    @type segment: VideoSegment
    """
    if segment is None:
        return row + ['', '', '', '', '', '', '', '','']
    return row + [segment.media_type, '' if segment.filename is None else os.path.basename(segment.filename),
                  segment.startframe, segment.endframe, segment.frames,
                  segment.starttime, segment.endtime, segment.rate, segment.error]


def archive_probes(project, directory='.', archive=True, reproduceMask= True, composite_names=['EmptyCompositeBuilder']):
    from maskgen import mask_rules
    """
    Create an archive containing probe files and CSV file describing the probes.

    :param project:  project (tgz or directory) location
    :param directory: location to place archive
    :return:
    @param project: str
    @param directory: str
    """
    if type(project) in [unicode,str]:
        logging.debug('Loading from {}'.format(project))
        scModel = ImageProjectModel(project)
    else:
        scModel = project
    if reproduceMask:
        for edge_id in scModel.getGraph().get_edges():
            scModel.reproduceMask(edge_id=edge_id)
    generator = ProbeGenerator(scModel=scModel, processors=[ProbeSetBuilder(scModel, compositeBuilders=[getattr(mask_rules,n) for n in composite_names]),
                                                            DetermineTaskDesignation(scModel, inputFunction=fetch_qaData_designation)])
    probes = generator()
    project_dir = scModel.get_dir()
    csvfilename = os.path.join(project_dir, 'probes.csv')
    items_to_archive = []

    def check_file(probe, description, project_dir, file_name):
        if os.path.exists(os.path.join(project_dir, file_name)):
            return
        logging.getLogger('maskgen').error('Target probe file missing {} for {}:{}:{}'.format(file_name, description, probe.finalNodeId,str(probe.edgeId)))

    with open(csvfilename, 'w') as outputfile:
        csvwriter = csv.writer(outputfile, delimiter=',')
        for probe in probes:
            base_node = scModel.getGraph().get_node(probe.targetBaseNodeId)
            final_node = scModel.getGraph().get_node(probe.finalNodeId)
            items_to_archive.append(base_node['file'])
            items_to_archive.append(final_node['file'])
            if probe.donorBaseNodeId is not None:
                donor_node = scModel.getGraph().get_node(probe.donorBaseNodeId)
                items_to_archive.append(donor_node['file'])
            else:
                donor_node = None
            if probe.donorMaskFileName is not None:
                check_file(probe, 'donor mask', project_dir,probe.donorMaskFileName)
                items_to_archive.append(os.path.basename(probe.donorMaskFileName))
            if probe.targetMaskFileName is not None:
                check_file(probe, 'target mask', project_dir, probe.targetMaskFileName)
                items_to_archive.append(os.path.basename(probe.targetMaskFileName))
            if probe.composites is not None:
                for k,b in probe.composites.iteritems():
                    if 'file name' in b:
                        check_file(probe, 'composite mask [{}]]'.format(k), project_dir, b['file name'])
            edge = scModel.getGraph().get_edge(probe.edgeId[0], probe.edgeId[1])
            csvwriter.writerow(append_segment(['summary',
                                               probe.edgeId[0],
                                               probe.edgeId[1],
                                               edge['op'],
                                               base_node['file'],
                                               final_node['file'],
                                               '' if probe.targetMaskFileName is None else os.path.basename(
                                                   probe.targetMaskFileName),
                                               '' if donor_node is None else donor_node['file'],
                                               '' if probe.donorMaskFileName is None else os.path.basename(
                                                   probe.donorMaskFileName)],
                                              None))
            for donor_segment in (probe.donorVideoSegments if probe.donorVideoSegments is not None else []):
                if donor_segment.filename is not None and len(donor_segment.filename) > 0:
                    check_file(probe, 'donor segment mask', project_dir, donor_segment.filename)
                    items_to_archive.append(os.path.basename(donor_segment.filename))
                csvwriter.writerow(append_segment(['donor_segment',
                                                   probe.edgeId[0],
                                                   probe.edgeId[1],
                                                   edge['op'],
                                                   base_node['file'],
                                                   final_node['file'],
                                                   '',
                                                   '',
                                                   ''],
                                                  donor_segment))
            for video_segment in (probe.targetVideoSegments if probe.targetVideoSegments is not None else []):
                if video_segment.filename is not None and len(video_segment.filename) > 0:
                    check_file(probe, 'target segment mask', project_dir, video_segment.filename)
                    items_to_archive.append(os.path.basename(video_segment.filename))
                csvwriter.writerow(append_segment(['target_segment',
                                                   probe.edgeId[0],
                                                   probe.edgeId[1],
                                                   edge['op'],
                                                   base_node['file'],
                                                   final_node['file'],
                                                   '',
                                                   '',
                                                   ''],
                                                  video_segment))

    for item in items_to_archive:
        if os.path.exists(os.path.join(project_dir, item)):
            continue
        logging.getLogger('maskgen').error('Target probe file missing {}')

    if archive:
        fname = os.path.join(directory, scModel.getName() + '.tgz')
        archive_file = tarfile.open(fname, "w:gz", errorlevel=2)
        # retain the CSV file in the archive
        items_to_archive.append(os.path.basename(csvfilename))
        # insure unique file names, as probes often reference the same image files (donors and targets)
        items_to_archive = set(items_to_archive)
        # move all files of interest into the archive
        for item in items_to_archive:
            archive_file.add(os.path.join(project_dir, item),
                        arcname=os.path.join(scModel.getName(), item))
        archive_file.close()


class ProbeGenerator:

    def __init__(self, scModel, processors = []):
        self.scModel = scModel
        self.processors = processors

    def __call__(self, inclusionFunction= isEdgeLocalized,
                                     saveTargets=True,
                                     graph=None,
                                     constructDonors=True,
                                     keepFailures=False,
                                     exclusions={},
                                     checkEmptyMask=True,
                                     audioToVideo=False,
                                     notifier=None):
        """
        :param inclusionFunction: filter out edges to not include in the probe set
        :param saveTargets: save the result images as files
        :param graph: the ImageGraph
        :param exclusions: dictionary of key value exclusion rules.  These rules apply to specific
        subtypes of meta-data such as inputmasks for paste sampled or neighbor masks for seam carving
        The agreed set of rules will evolve and is particular to the function.
        Exclusion starts with the scope and then the paramater such as seam_carving.vertical or
        global.inputmaskname.
        :param audioToVideo: If true, create video masks for audio masks, providing there are no audio masks.
        :return: The set of probes
        @rtype: list [Probe]
        """

        self.scModel._executeSkippedComparisons()
        thread_pool = MaskgenThreadPool(int(prefLoader.get_key('skipped_threads', 2)))
        futures = list()
        useGraph = graph if graph is not None else self.scModel.G
        for edge_id in useGraph.get_edges():
            edge = useGraph.get_edge(edge_id[0], edge_id[1])
            if inclusionFunction(edge_id, edge, self.scModel.gopLoader.getOperationWithGroups(edge['op'],fake=True)):
                composite_generator = prepareComposite(edge_id, useGraph, self.scModel.gopLoader, self.scModel.probeMaskMemory, notifier=notifier)
                futures.append(thread_pool.apply_async(composite_generator.constructProbes, args=(),kwds={
                    'saveTargets':saveTargets,
                    'inclusionFunction':inclusionFunction,
                    'constructDonors':constructDonors,
                    'keepFailures':keepFailures,
                    'exclusions':exclusions,
                    'checkEmptyMask':checkEmptyMask,
                    'audioToVideo':audioToVideo
                }))
        probes = list()
        for future in futures:
            probes.extend(future.get(timeout=int(prefLoader.get_key('probe_timeout', 100000))))
        return self.apply_processors(probes)

    def apply_processors(self, probes = []):
        for processor in self.processors:
            probes = processor.apply(probes)
        return probes

class ProbeProcessor:

    def __init__(self, scModel):
        self.scModel = scModel

    def apply(self, probes = []):
        return probes

class ProbeSetBuilder(ProbeProcessor):

    def __init__(self, scModel=None, compositeBuilders=[ColorCompositeBuilder]):
        ProbeProcessor.__init__(self, scModel=scModel)
        self.compositeBuilders = compositeBuilders

    def probeCompare(self, x, y):
        """

        :param x:
        :param y:
        :return:
        @type x: Probe
        @type y: Probe
        """
        diff = cmp(x.finalImageFileName, y.finalImageFileName)
        if diff == 0:
            diff = x.level - y.level
            if diff == 0:
                return cmp(str(x.edgeId), str(y.edgeId))
        return diff

    def apply(self, probes = []):
        """
        :param probes:
        :return:
        @type probes : list(Probe)
        """
        probes = sorted(probes, cmp=self.probeCompare)
        localCompositeBuilders = [cb() for cb in self.compositeBuilders]
        for compositeBuilder in localCompositeBuilders:
            compositeBuilder.initialize(self.scModel.G, probes)
        maxpass = max([compositeBuilder.passes for compositeBuilder in localCompositeBuilders])
        composite_bases = dict()
        for passcount in range(maxpass):
            for probe in probes:
                if probe.targetMaskImage is None:
                    continue
                composite_bases[probe.finalNodeId] = probe.targetBaseNodeId
                edge = self.scModel.G.get_edge(probe.edgeId[0], probe.edgeId[1])
                for compositeBuilder in localCompositeBuilders:
                    compositeBuilder.build(passcount, probe, edge)
        for compositeBuilder in localCompositeBuilders:
            compositeBuilder.finalize(probes)
        return probes


def default_designation(scModel, probe, allow_video_spatial=False):
    ftype = scModel.getNodeFileType(probe.targetBaseNodeId)
    len_all_masks = len(probe.targetVideoSegments if probe.targetVideoSegments is not None else [])
    len_spatial_masks = len([x for x in probe.targetVideoSegments if
                             x.filename is not None] if probe.targetVideoSegments is not None else [])
    has_video_masks = len_all_masks > 0
    spatial_temporal = has_video_masks and len_spatial_masks > 0
    if ftype == 'image':
        if probe.targetMaskImage != None:
            return 'spatial'
    elif has_video_masks:
        return 'spatial-temporal' if spatial_temporal and allow_video_spatial else 'temporal'
    return 'detect'

def fetch_qaData_designation(scModel, probe):
    from maskgen.notifiers import QaNotifier
    from maskgen.qa_logic import ValidationData
    qa_notify = scModel.notify.get_notifier_by_type(QaNotifier)
    if qa_notify is not None:
        qadata = qa_notify.qadata if qa_notify.qadata != None else ValidationData(scModel)
        link = qadata.make_link_from_probe(probe)
        if link is not None:
            des = qadata.get_qalink_designation(link)
            if des not in [None,'']:
                return des
    return default_designation(scModel, probe)

class DetermineTaskDesignation(ProbeProcessor):
    """
        Task designation is determined by presence of spatial and temporal components
        Use inputFunction on init to pull designation from elsewhere- otherwise, automatic designation will be made.
    """

    def __init__(self, scModel = None, inputFunction = None):
        ProbeProcessor.__init__(self, scModel= scModel)
        self.inputFunction = inputFunction


    def apply(self, probes = []):
        """
        :param probes:
        :return:
        @type probes : list(Probe)
        """
        for probe in probes:
            if self.inputFunction is not None:
                probe.taskDesignation = self.inputFunction(self.scModel, probe)
            else:
                probe.taskDesignation = default_designation(self.scModel, probe, True)
        return probes

class DropVideoFileForNonSpatialDesignation(ProbeProcessor):
    """
        Probes have been set to not use spatial shoudl drop their file.
    """

    def __init__(self):
        ProbeProcessor.__init__(self,None)

    def apply(self, probes = []):
        """
        :param probes:
        :return:
        @type probes : list(Probe)
        """
        for probe in probes:
            if probe.taskDesignation not in  ['spatial','spatial-temporal']:
                for videoSegment in probe.targetVideoSegments:
                    videoSegment.filename = None
        return probes

class ExtendProbesForDetectEdges(ProbeProcessor):
    """
        Probes have been set to not use spatial shoudl drop their file.
    """

    def __init__(self, scModel,selectionCriteria):
        """

        :param scModel:
        :param selectionCriteria:
        @type scModel: ImageProjectModel
        @typpe selectionCriteria: ()
        """

        self.selectionCriteria = selectionCriteria
        ProbeProcessor.__init__(self,scModel)

    def apply(self, probes = []):
        """
        :param probes:
        :return:
        @type probes : list(Probe)
        """
        edges = set()
        for probe in probes:
            edges.add(probe.edgeId)
        new_probes = []
        for edge_id in self.scModel.getGraph().get_edges():
            if edge_id not in edges:
                edge = self.scModel.getGraph().get_edge(edge_id[0],edge_id[1])
                if self.selectionCriteria(edge):
                    base_nodes = self.scModel._findBaseNodes(edge_id[0], excludeDonor=True)
                    base_nodes = [node for node in base_nodes
                                  if self.scModel.getGraph().get_node(node)['nodetype'] == 'base']
                    donor_nodes = self.scModel._findBaseNodes(edge_id[0], excludeDonor=False)
                    donor_nodes = [n for n in donor_nodes if n not in base_nodes]
                    donor_nodes = [None] if len(donor_nodes) == 0 else donor_nodes
                    terminal_nodes = self.scModel._findTerminalNodes(edge_id[1], excludeDonor=True)
                    for base_node in base_nodes:
                        for terminal_node in terminal_nodes:
                            for donor_node in donor_nodes:
                                new_probes.append(
                                    Probe(edge_id,
                                          terminal_node,
                                          base_node,
                                          donor_node,
                                          targetVideoSegments=[], taskDesignation='detect'))
        return probes + new_probes

class CompositeExtender:

    """ All masks in a color composite up to and through the current operation
    """
    def __init__(self, scModel):
        """
        :param scModel:
        @type scModel: ImageProjectModel
        """
        self.scModel = scModel
        self.prior_probes = None

    def extendCompositeByOne(self, probes, start=None, override_args={}):
        """
        :param compositeMask:
        :param level:
        :param replacementEdgeMask:
        :param colorMap:
        :param override_args:
        :return:
        @type compositeMask: ImageWrapper
        @type level: IntObject
        @type replacementEdgeMask: ImageWrapper
        @rtype ImageWrapper
        """
        results = findBaseNodesWithCycleDetection(self.scModel.getGraph(), start if start is not None else \
            (self.scModel.end if self.scModel.end is not None else self.scModel.start))
        if len(results) == 0:
            return
        nodeids = results[0][2]
        graph = self.scModel.getGraph().subgraph(nodeids)
        composite_generator = prepareComposite((self.scModel.start,self.scModel.end), graph, self.scModel.getGroupOperationLoader(),
                                                          self.scModel.probeMaskMemory)
        probes = composite_generator.extendByOne(probes,self.scModel.start,self.scModel.end,override_args=override_args)

        return ProbeSetBuilder(self.scModel).apply(probes)

    def constructPathProbes(self, start=None, constructDonors=True):
        """
         Construct the composite mask for the selected node.
         Does not save the composite in the node.
         Returns the composite mask if successful, otherwise None
        """
        results = findBaseNodesWithCycleDetection(self.scModel.getGraph(), start if start is not None else \
            (self.scModel.end if self.scModel.end is not None else self.scModel.start))
        if len(results) == 0:
            return
        nodeids = results[0][2]
        graph = self.scModel.getGraph().subgraph(nodeids)
        generator = ProbeGenerator(scModel=self.scModel, processors=[ProbeSetBuilder(self.scModel)])
        probes = generator(graph=graph,saveTargets=False,inclusionFunction=isEdgeComposite, constructDonors=constructDonors)
        return probes

    def get_image(self, override_args={}, target_size=(0,0)):
        if self.prior_probes is None:
            self.prior_probes = self.constructPathProbes(start=self.scModel.start, constructDonors=False)

        if self.scModel.getDescription() is None or not self.prior_probes:
            probes = self.prior_probes
        else:
            probes = self.extendCompositeByOne(self.prior_probes,
                                                override_args=override_args)
        if probes:
            composite = probes[-1].composites['color']['image']
            if composite.size != target_size:
                composite = composite.resize(target_size,Image.ANTIALIAS)
            return composite
        return ImageWrapper(np.zeros((target_size[1], target_size[0]), dtype='uint8'))

class DonorExtender:

    def __init__(self, scModel):
        self.scModel = scModel

    def get_image(self, override_args={},target_size=(0,0)):
        return ImageWrapper(np.zeros((target_size[1],target_size[0]),dtype='uint8'))

def cleanup_temporary_files(probes = [], scModel = None):
    files_to_remove = []

    used_hdf5 = ['']
    used_masks = ['']
    for frm, to in scModel.G.get_edges():
        edge = scModel.G.get_edge(frm, to)
        input_mask = getValue(edge, 'inputmaskname', '')
        video_input_mask = getValue(edge, 'arguments.videomaskname', '')
        subs = getValue(edge, 'substitute videomasks', [])
        for sub in subs:
            hdf5 = get_file_from_segment(sub)
            used_hdf5.append(hdf5)
        mask = getValue(edge, 'maskname', '')
        used_masks.append(input_mask)
        used_masks.append(video_input_mask)
        used_masks.append(mask)
        videomasks = getValue(edge, 'videomasks', [])
        for mask in videomasks:
            hdf5 = get_file_from_segment(mask)
            used_hdf5.append(hdf5)
    used_hdf5 = set(used_hdf5)
    used_masks = set(used_masks)

    for probe in probes:
        mask = probe.targetMaskFileName if probe.targetMaskFileName != None else ''
        if os.path.basename(mask) not in used_masks:
            files_to_remove.append(mask)
        if probe.targetVideoSegments != None:
            for segment in probe.targetVideoSegments:
                hdf5 = segment.filename if segment.filename != None else ''
                if os.path.basename(hdf5) not in used_hdf5:
                    files_to_remove.append(hdf5)

    files_to_remove = set(files_to_remove)

    for _file in files_to_remove:
        try:
            os.remove(os.path.join(scModel.get_dir(), _file))
        except OSError:
            pass


def main():
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--specification', required=True, help='JSON File')
    parser.add_argument('--composites', required=False, nargs='+', help='Composites to use')
    args = parser.parse_args(sys.argv[1:])
    archive_probes(args.specification,composite_names=['EmptyCompositeBuilder'] if args.composites is None else args.composites)

if __name__ == '__main__':
    main()
