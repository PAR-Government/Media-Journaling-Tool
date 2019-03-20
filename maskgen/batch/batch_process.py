# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
#

"""
  Batch Journal Extensions Processing
"""

from __future__ import print_function
import argparse
import sys
from maskgen.software_loader import *
from maskgen import scenario_model
import maskgen.tool_set
import bulk_export
import maskgen.group_operations
import maskgen
from maskgen.batch import pick_projects, BatchProcessor, pick_zipped_projects
from batch_project import loadJSONGraph, BatchProject, updateAndInitializeGlobalState
from maskgen.image_graph import extract_archive
from maskgen.userinfo import setPwdX, CustomPwdX
from maskgen.loghandling import set_logging,set_logging_level
from maskgen.plugins import EchoInterceptor


def parseRules(extensionRules):
    return extensionRules.split(',') if extensionRules is not None else []

def findNodesToExtend(sm, rules):
    """

    :param sm:
    :param rules:
    :return:
    @type sm: scenario_model.ImageProjectModel
    """
    nodes = []
    for nodename in sm.getNodeNames():
        baseNodeName = sm.getBaseNode(nodename)
        node = sm.getGraph().get_node(nodename)
        baseNode = sm.getGraph().get_node(baseNodeName)
        if (baseNode['nodetype'] != 'base') and 'donorpath' not in rules:
            continue
        isBaseNode = node['nodetype'] == 'base' or len(sm.getGraph().predecessors(nodename)) == 0
        ops = []
        isSourceOutput = False
        isSourceAntiForensic = False
        isTargetAntiForensic = False
        isTargetOutput = False
        op = None
        if not isBaseNode:
            for predecessor in sm.getGraph().predecessors(nodename):
                edge = sm.getGraph().get_edge(predecessor, nodename)
                if edge['op'] == 'Donor':
                    continue
                op = sm.getGroupOperationLoader().getOperationWithGroups(edge['op'], fake=True)
                ops.append(edge['op'])
                isTargetOutput |= op.category == 'Output'
                isTargetAntiForensic |= op.category == 'AntiForensic'
            for successor in sm.getGraph().successors(nodename):
                edge = sm.getGraph().get_edge(nodename, successor)
                if edge['op'] == 'Donor':
                    continue
                succ_op = sm.getGroupOperationLoader().getOperationWithGroups(edge['op'], fake=True)
                ops.append(edge['op'])
                isSourceOutput |= succ_op.category == 'Output'
                isSourceAntiForensic |= succ_op.category == 'AntiForensic'
        skip=False
        for rule in rules:
                if rule.startswith('+'):
                    catandop = rule[1:].split(':')
                    if op is not None:
                        if (op.category == catandop[0] or catandop[0] == '') and \
                                catandop[1] == op.name:
                            nodes.append(nodename)
                            skip = True
                            break
        if (node['nodetype'] == 'final' or len(sm.getGraph().successors(nodename)) == 0):
            if 'finalnode' in rules:
                nodes.append(nodename)
            if 'finalpng' in rules and sm.getGraph().get_filename(nodename).lower().endswith('png'):
                nodes.append(nodename)
            continue
        if (isTargetOutput and 'outputop' not in rules) or\
            (isTargetAntiForensic and 'antiforensicop' not in rules):
            continue
        if (isSourceOutput and 'outputsourceop' in rules) or \
            (isSourceAntiForensic and 'antiforensicsourceop' in rules):
            nodes.append(nodename)
            continue
        if isBaseNode and 'basenode' not in rules:
            continue
        for rule in rules:
                if rule.startswith('~'):
                    catandop = rule[1:].split(':')
                    if op is not None:
                        if (op.category == catandop[0] or catandop[0] == '') and \
                                (len(catandop) == 0 or len(catandop[1]) == 0 or catandop[1] == op.name):
                            skip= True
                            break
        if not skip:
            nodes.append(nodename)
    return nodes


def _processProject(batchSpecification, extensionRules, project, workdir=None, global_state=dict()):
    """

    :param batchSpecification:
    :param extensionRules:
    :param project:
    :return:
    @type batchSpecification: BatchProject
    """
    sm = maskgen.scenario_model.ImageProjectModel(project,tool='jtprocess')
    nodes = findNodesToExtend(sm, extensionRules)
    print ('extending {}'.format(' '.join(nodes)))
    if not batchSpecification.executeForProject(sm, nodes,workdir=workdir,global_variables=global_state):
        raise ValueError('Failed to process {}'.format(sm.getName()))
    sm.save()
    return sm


def processZippedProject(batchSpecification, extensionRules, project, workdir=None, global_state=dict()):
    import tempfile
    import shutil
    dir = tempfile.mkdtemp()
    try:
        extract_archive(project, dir)
        for project in pick_projects(dir):
            sm = _processProject(batchSpecification, extensionRules, project,
                                 workdir=workdir,
                                 global_state=global_state)
            sm.export(workdir)
    finally:
        shutil.rmtree(dir)


def processAnyProject(batchSpecification, extensionRules, outputGraph, workdir, global_state, project):
    from maskgen.graph_output import ImageGraphPainter
    """
    :param project:
    :return:
    @type project: str
    """
    if project.endswith('tgz'):
        processZippedProject(batchSpecification, extensionRules, project,
                             workdir=workdir,
                             global_state=global_state)
    else:
        sm = _processProject(batchSpecification, extensionRules, project,
                             workdir=workdir,
                             global_state=global_state)
        if outputGraph:
            summary_file = os.path.join(sm.get_dir(), '_overview_.png')
            try:
                ImageGraphPainter(sm.getGraph()).output(summary_file)
            except Exception as e:
                logging.getLogger('maskgen').error("Unable to create image graph: " + str(e))
    return []


def processSpecification(specification,
                         extensionRules,
                         projects_directory,
                         completeFile=None,
                         outputGraph=False,
                         threads=1,
                         loglevel=None,
                         global_variables='',
                         initializers=None,
                         skipValidation=False,
                         passthrus=[]):
    """
    Perform a plugin operation on all projects in directory
    :param projects_directory: directory of projects
    :param extensionRules: rules that determine which nodes are extended
    :param specification:  the specification file (see batch project)
    :return: None
    """
    from functools import partial
    batch = loadJSONGraph(specification)
    rules = parseRules(extensionRules)
    global_state = updateAndInitializeGlobalState(dict(), global_variables, initializers)
    global_state['skipvalidation'] = skipValidation
    if len(passthrus) > 0:
        global_state['passthrus'] = passthrus
    if loglevel is not None:
            logging.getLogger('maskgen').setLevel(logging.INFO if loglevel is None else int(loglevel))
            set_logging_level(logging.INFO if loglevel is None else int(loglevel))
    if batch is None:
        return
    iterator = pick_projects(projects_directory)
    iterator.extend(pick_zipped_projects(projects_directory))
    processor = BatchProcessor(completeFile, iterator, threads=threads)
    func = partial(processAnyProject, batch, rules, outputGraph, '.', global_state)
    return processor.process(func)


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('--projects', default=None, help='Projects directory')
    parser.add_argument('--extensionRules', default=None, help='List of rules to select nodes to extend')
    parser.add_argument('--specification', default=None, help='Extend projects using batch project specifications')
    parser.add_argument('--completeFile', default=None, help='A file recording completed projects')
    parser.add_argument('--username', default=None, help='Username for projects')
    parser.add_argument('--organization', default=None, help='User\'s Organization')
    parser.add_argument('--s3', default=None, help='S3 Bucket/Path to upload projects to')
    parser.add_argument('--graph', action='store_true', help='Output Summary Graph')
    parser.add_argument('--threads', default='1', help='Number of Threads')
    parser.add_argument('--loglevel', required=False, help='log level')
    parser.add_argument('--global_variables', required=False, help='global state initialization')
    parser.add_argument('--initializers', required=False, help='global state initialization')
    parser.add_argument('--skip_validation', required=False, action='store_true')
    parser.add_argument('--test', required=False,action='store_true', help='test extension')
    parser.add_argument('--passthrus', required=False, default='none', help='plugins to passthru')

    args = parser.parse_args(argv)

    setPwdX(CustomPwdX(args.username))
    manager = maskgen.plugins.loadPlugins()
    if args.test:
        EchoInterceptor(manager.getBroker())
        if args.projects is None:
            print ('argument projects is required')
            sys.exit(-1)
    processSpecification(args.specification,
                         args.extensionRules,
                         args.projects,
                         completeFile=args.completeFile,
                         outputGraph=args.graph,
                         threads=int(args.threads),
                         loglevel=args.loglevel,
                         global_variables=args.global_variables,
                         initializers=args.initializers,
                         skipValidation=args.skip_validation,
                         passthrus=args.passthrus.split(',') if args.passthrus != 'none' else [])

    # bulk export to s3
    if args.s3:
        bulk_export.upload_projects(args.s3, args.projects)


if __name__ == '__main__':
    main(sys.argv[1:])
