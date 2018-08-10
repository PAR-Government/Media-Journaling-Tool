# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import os
import maskgen.scenario_model
from maskgen.tool_set import *
import tarfile
import csv
from maskgen.mask_rules import EmptyCompositeBuilder
from maskgen.mask_rules import VideoSegment

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


def archive_probes(project, directory='.', archive=True, reproduceMask= True):
    """
    Create an archive containing probe files and CSV file describing the probes.

    :param project:  project (tgz or directory) location
    :param directory: location to place archive
    :return:
    @param project: str
    @param directory: str
    """
    if type(project) in ['unicode','str']:
        scModel = maskgen.scenario_model.ImageProjectModel(project)
    else:
        scModel = project
    if reproduceMask:
        for edge_id in scModel.getGraph().get_edges():
            scModel.reproduceMask(edge_id=edge_id)
    probes = scModel.getProbeSet(compositeBuilders=[EmptyCompositeBuilder])
    project_dir = scModel.get_dir()
    csvfilename = os.path.join(project_dir, 'probes.csv')
    items_to_archive = []
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
                items_to_archive.append(os.path.basename(probe.donorMaskFileName))
            if probe.targetMaskFileName is not None:
                items_to_archive.append(os.path.basename(probe.targetMaskFileName))
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

def main():
    import sys
    archive_probes(sys.argv[1])

if __name__ == '__main__':
    main()
