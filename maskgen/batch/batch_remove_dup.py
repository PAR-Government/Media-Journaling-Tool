# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from __future__ import print_function

import sys
import argparse
import maskgen.scenario_model
from maskgen.batch import pick_projects, BatchProcessor
from  maskgen.tool_set import getValue
from maskgen.software_loader import getOperation
import os
from maskgen.graph_output import ImageGraphPainter

def fix_projects(args, projectNAme):
    """
    """
    project = maskgen.scenario_model.loadProject(projectNAme)
    finalNodes = []
    # check for disconnected nodes
    # check to see if predecessors > 1 consist of donors
    graph = project.getGraph()
    finalfiles = set()

    for edge_id in graph.get_edges():
        edge = graph.get_edge(edge_id[0], edge_id[1])
        if edge is None:
            continue
        op = getOperation(edge['op'])
        if getValue(edge, 'empty mask') == 'yes' and 'checkEmpty' in op.rules:
            project.select((edge_id[0], edge_id[1]))
            project.remove(children=True)

    for node in graph.get_nodes():
        successors = graph.successors(node)
        if len(successors) == 0:
            finalNodes.append(node)

    duplicates = dict()
    for node in finalNodes:
        filename = graph.get_node(node)['file']
        if filename in finalfiles and filename not in duplicates:
            duplicates[filename] = node
        finalfiles.add(filename)

    for k,v in duplicates.iteritems():
        project.selectImage(v)
        project.remove()
        print ('delete ' + v)

    project.save()

    #summary_file = os.path.join(graph.dir, '_overview_.png')
    #ImageGraphPainter(graph).output(summary_file)
    return []

def main(argv=sys.argv[1:]):
    from functools import partial
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads', default=1, required=False, help='number of projects to build')
    parser.add_argument('-d', '--projects', help='directory of projects')
    parser.add_argument('--completeFile', default=None, help='A file recording completed projects')
    args = parser.parse_args(argv)

    iterator = pick_projects(args.projects)
    processor = BatchProcessor(args.completeFile, iterator, threads=args.threads)
    func = partial(fix_projects, args)
    return processor.process(func)


if __name__ == '__main__':
    main(sys.argv[1:])

