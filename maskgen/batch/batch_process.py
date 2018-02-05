"""
Bulk Image Journal Processing
"""
from __future__ import print_function
import argparse
import sys
import itertools
import rawpy
from maskgen.software_loader import *
from maskgen import scenario_model
from maskgen import graph_rules
import maskgen.tool_set
import bulk_export
import maskgen.group_operations
import maskgen
from maskgen.batch import pick_projects, BatchProcessor, pick_zipped_projects
from batch_project import loadJSONGraph, BatchProject
from maskgen.image_graph import extract_archive
from maskgen.tool_set import setPwdX, CustomPwdX



def args_to_map(args, op):
    if len(args) > 0:
        parsedArgs = dict(itertools.izip_longest(*[iter(args)] * 2, fillvalue=""))
        for key in parsedArgs:
            parsedArgs[key] = maskgen.tool_set.validateAndConvertTypedValue(key, parsedArgs[key], op,
                                                                            skipFileValidation=False)
    else:
        parsedArgs = {}
    return parsedArgs


def check_additional_args(parsedArgs, op, continueWithWarning=False):
    """
    Parse additional arguments (rotation, etc.) and validate
    :param additionalArgs: user input list of additional parameters e.g. [rotation, 60...]
    :param op: operation object (use software_loader.getOperation('operationname')
    :return: dictionary containing parsed arguments e.g. {rotation: 60}
    """
    # parse additional arguments (rotation, etc.)
    # http://stackoverflow.com/questions/6900955/python-convert-list-to-dictionary
    if op is None:
        print ('Invalid Operation Name {}'.format(op))
        return {}

    missing = [param for param in op.mandatoryparameters.keys() if
               (param not in parsedArgs or len(str(parsedArgs[param])) == 0) and
               param != 'inputmaskname' and
               ('source' not in op.mandatoryparameters[param] or op.mandatoryparameters[param]['source'] == 'image')]

    inputmasks = [param for param in op.optionalparameters.keys() if param == 'inputmaskname' and
                  'purpose' in parsedArgs and parsedArgs['purpose'] == 'clone']

    if ('inputmaskname' in op.mandatoryparameters.keys() or 'inputmaskname' in inputmasks) and (
                        'inputmaskname' not in parsedArgs or parsedArgs['inputmaskname'] is None or len(
                parsedArgs['inputmaskname']) == 0):
        missing.append('inputmaskname')

    if missing:
        for m in missing:
            print ('Mandatory parameter ' + m + ' is missing')
        if continueWithWarning is False:
            sys.exit(0)
    return parsedArgs


def find_corresponding_image(image, imageList):
    """
    Find image file best matching image arg in imageList
    :param image: image to match
    :param imageList: list of images
    :return: the name of best matching image
    """
    set = [x for x in imageList if image in x]
    set.sort()
    return set[0]


def find_json_path(image, dir):
    """
    Returns full JSON path (with .json filename included at end).
    Creates project directory if necessary.
    DOES NOT create a JSON file, however.
    :param image: str containing base image name
    :param dir: project directory (subdirectory will be created here if necessary)
    :return: full JSON path
    """
    for f in os.listdir(dir):
        if f in image:
            # ex. f = myproject, image = myproject_01.png
            return os.path.join(dir, f, f + '.json')

    prjDir = os.path.join(dir, image)
    jsonPath = os.path.join(prjDir, image + '.json')

    # create project/json directory if doesn't exist
    if not os.path.exists(prjDir):
        os.makedirs(prjDir)
    return jsonPath


def create_image_list(fileList):
    """
    Take images from a file list and put them in a new list
    :param fileList: list of files
    :return: list of image files in fileList
    """
    ext = [x[1:] for x in maskgen.tool_set.suffixes]
    return [i for i in os.listdir(fileList) if len([e for e in ext if i.lower().endswith(e)]) > 0]


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
        if (node['nodetype'] == 'final' or len(sm.getGraph().successors(nodename)) == 0) and 'finalnode' not in rules:
            continue
        isBaseNode = node['nodetype'] == 'base' or len(sm.getGraph().predecessors(nodename)) == 0
        if isBaseNode and 'basenode' not in rules:
            continue
        ops = []
        isOutput = False
        isAntiForensic = False
        op = None
        if not isBaseNode:
            for predecessor in sm.getGraph().predecessors(nodename):
                edge = sm.getGraph().get_edge(predecessor, nodename)
                if edge['op'] == 'Donor':
                    continue
                op = sm.getGroupOperationLoader().getOperationWithGroups(edge['op'], fake=True)
                ops.append(edge['op'])
                isOutput |= op.category == 'Output'
                isAntiForensic |= op.category == 'AntiForensic'
        if isOutput and 'outputop' not in rules:
            continue
        if isAntiForensic and 'antiforensicop' not in rules:
            continue
        for rule in rules:
            if rule.startswith('~'):
                catandop = rule[1:].split(':')
                if op is not None:
                    if op.category == catandop[0] and \
                            (len(catandop) == 0 or len(catandop[1]) == '' or catandop[1] == op.name):
                        continue
        nodes.append(nodename)
    return nodes


def _processProject(batchSpecification, extensionRules, project, workdir=None):
    """

    :param batchSpecification:
    :param extensionRules:
    :param project:
    :return:
    @type batchSpecification: BatchProject
    """
    sm = maskgen.scenario_model.ImageProjectModel(project)
    nodes = findNodesToExtend(sm, extensionRules)
    print ('extending {}'.format(' '.join(nodes)))
    if not batchSpecification.executeForProject(sm, nodes,workdir=workdir):
        raise ValueError('Failed to process {}'.format(sm.getName()))
    sm.save()
    return sm


def processZippedProject(batchSpecification, extensionRules, project,workdir=None):
    import tempfile
    import shutil
    dir = tempfile.mkdtemp()
    try:
        extract_archive(os.path.join(dir, project), dir)
        for project in pick_projects(dir):
            sm = _processProject(batchSpecification, extensionRules, project,workdir=workdir)
            sm.export(os.path.join(dir, project))
    finally:
        shutil.rmtree(dir)


def processAnyProject(batchSpecification, extensionRules, outputGraph, workdir, project):
    from maskgen.graph_output import ImageGraphPainter
    """
    :param project:
    :return:
    @type project: str
    """
    if project.endswith('tgz'):
        processZippedProject(batchSpecification, extensionRules, project,workdir=workdir)
    else:
        sm = _processProject(batchSpecification, extensionRules, project,workdir=workdir)
        if outputGraph:
            summary_file = os.path.join(sm.get_dir(), '_overview_.png')
            try:
                ImageGraphPainter(sm.getGraph()).output(summary_file)
            except Exception as e:
                logging.getLogger('maskgen').error("Unable to create image graph: " + str(e))
    return []


def processSpecification(specification, extensionRules, projects_directory, completeFile=None, outputGraph=False,
                         threads=1, loglevel=None):
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
    if batch is None:
        return
    iterator = pick_projects(projects_directory)
    iterator.extend(pick_zipped_projects(projects_directory))
    processor = BatchProcessor(completeFile, iterator, threads=threads)
    func = partial(processAnyProject, batch, rules, outputGraph, '.')
    return processor.process(func)


def process(sourceDir, endDir, projectDir, op, software, version, opDescr, inputMaskPath, arguments,
            props):
    """
    Perform the bulk journaling. If no endDir is specified, it is assumed that the user wishes
    to add on to existing projects in projectDir.
    :param sourceDir: Directory of source images
    :param endDir: Directory of manipulated images (1 manipulation stage). Optional.
    :param projectDir: Directory for projects to be placed
    :param opDescr: Operation performed between source and ending dir
    :param software: Manipulation software used
    :param version: Version of manipulation software
    :param descr: Description of manipulation. Optional
    :param inputMaskPath: Directory of input masks. Optional.
    :param arguments: Dictionary of additional args ({rotation:90,...})
    :param props: Dictionary containing project properties
    :return: None
    """

    startingImages = create_image_list(sourceDir)

    # Decide what to do with input (create new or add)
    if endDir:
        endingImages = create_image_list(endDir)
    else:
        endingImages = None

    if inputMaskPath:
        inputMaskImages = create_image_list(inputMaskPath)
    else:
        inputMaskImages = None

    # begin looping through the different projects
    total = len(startingImages)
    processNo = 1

    for sImg in startingImages:

        sImgName = ''.join(sImg.split('.')[:-1])
        if inputMaskPath:
            maskIm = os.path.join(inputMaskPath, find_corresponding_image(sImgName, inputMaskImages))
        else:
            maskIm = None

        project = find_json_path(sImgName, projectDir)

        # open the project
        new = not os.path.exists(project)
        sm = maskgen.scenario_model.ImageProjectModel(project)
        if new:
            logging.getLogger('maskgen').info( 'Creating {}'.format(project))
            lastNodeName = sm.addImage(os.path.join(sourceDir, sImg))
            # lastNodeName = sImgName
            for prop, val in props.iteritems():
                sm.setProjectData(prop, val)
            eImg = None if endDir is None else os.path.join(endDir, find_corresponding_image(sImgName, endingImages))
        else:
            eImg = os.path.join(sourceDir, sImg)
            lastNodes = [n for n in sm.G.get_nodes() if len(sm.G.successors(n)) == 0]
            lastNodeName = lastNodes[-1]

        lastNode = sm.G.get_node(lastNodeName)
        sm.selectImage(lastNodeName)

        if software is not None or version is not None and op is not None and eImg is not None:
            # prepare details for new link
            softwareDetails = Software(software, version)
            if arguments:
                opDetails = maskgen.scenario_model.Modification(op, opDescr, software=softwareDetails,
                                                                inputMaskName=maskIm,
                                                                arguments=arguments, automated='yes')
            else:
                opDetails = maskgen.scenario_model.Modification(op, opDescr, software=softwareDetails,
                                                                inputMaskName=maskIm, automated='yes')

            position = ((lastNode['xpos'] + 50 if lastNode.has_key('xpos') else
                         80), (lastNode['ypos'] + 50 if lastNode.has_key('ypos') else 200))

            # create link
            sm.addNextImage(eImg, mod=opDetails,
                            sendNotifications=False, position=position)
            logging.getLogger('maskgen').info(
                'Operation {} complete on project ({}/{}): {}'.format( op,str(processNo), str(total),project))
        elif eImg is not None:
            logging.getLogger('maskgen').error( 'Operation, Software and Version need to be defined to complete the link.')
        sm.save()
        processNo += 1


def process_plugin(sourceDir, projects, plugin, props, arguments):
    """
    Perform a plugin operation on all projects in directory
    :param projects: directory of projects
    :param plugin: plugin to perform
    :return: None
    """
    if sourceDir:
        new = True
        iterator = create_image_list(sourceDir)
    else:
        new = False
        iterator = pick_projects(projects)

    total = len(iterator)
    processNo = 1
    for i in iterator:
        if new:
            sImgName = ''.join(i.split('.')[:-1])
            project = find_json_path(sImgName, projects)
            sm = maskgen.scenario_model.ImageProjectModel(project)
            for prop, val in props.iteritems():
                sm.setProjectData(prop, val)
            lastNode = sm.addImage(os.path.join(sourceDir, i))
        else:
            sm = maskgen.scenario_model.ImageProjectModel(i)
            lastNode = [n for n in sm.G.get_nodes() if len(sm.G.successors(n)) == 0][-1]

        sm.selectImage(lastNode)
        errors, pairs = sm.imageFromPlugin(plugin, **arguments)
        if errors is not None and len(errors) > 0:
            logging.getLogger('maskgen').error( 'Plugin {} on project {} failed: {}'.format(plugin,sm.getName(), errors))
        sm.save()
        if errors is None or len(errors) == 0:
            logging.getLogger('maskgen').info('Plugin operation {} on project {} complete ({}/{})'.format(
                plugin,sm.getName(),str(processNo),str(total)))
        processNo += 1


def process_jpg(projects):
    """
    Save image as JPEG using the q tables of the base image, and copy exif from base for all projects in directory.
    :param projects: directory of projects
    :return: None
    """
    projectList = pick_projects(projects)
    total = len(projectList)
    processNo = 1
    for project in projectList:
        sm = maskgen.scenario_model.loadProject(project)
        maskgen.plugins.loadPlugins()
        op = maskgen.group_operations.CopyCompressionAndExifGroupOperation(sm)
        op.performOp()
        sm.save()
        logging.getLogger('maskgen').info('Completed compression operation on project ({}/{}) {}'.format( str(processNo), str(total), project))
        processNo += 1


def parse_properties(sourceDir, endDir, plugin, specification, **kwargs):
    """
    Parse properties into dictionary
    :param kwargs: individual properties and values (e.g. technicalsummary='This is an example')
    :return: dictionary of properties
    """
    properties = {}
    if (sourceDir and endDir) or (sourceDir and (plugin or specification)):
        # projects will be new, so need to check properties
        for prop, val in kwargs.iteritems():
            if val is not None:
                if val is False:
                    val = 'no'
                elif val is True:
                    val = 'yes'
            properties[prop] = val

        # verify that all project-level properties are set
        for p in getProjectProperties():
            if not p.node and not p.readonly and p.rule is None and p.mandatory:
                if p.name not in properties:
                    sys.exit('Error: {} is required for new projects.'.format(p.name))
    return properties


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projects', default=None, help='Projects directory')
    parser.add_argument('--extensionRules', default=None, help='List of rules to select nodes to extend')
    parser.add_argument('--specification', default=None, help='Extend projects using batch project specifications')
    parser.add_argument('--completeFile', default=None, help='A file recording completed projects')
    parser.add_argument('--plugins', action='store_true', help='Dump plugin formation')
    parser.add_argument('--plugin', default=None, help='Perform specified plugin operation')
    parser.add_argument('--sourceDir', default=None, help='Directory of starting images')
    parser.add_argument('--endDir', default=None, help='Directory of manipulated images')
    parser.add_argument('--op', default=None, help='Operation Name')
    parser.add_argument('--softwareName', default=None, help='Software Name')
    parser.add_argument('--softwareVersion', default=None, help='Software Version')
    parser.add_argument('--description', default=None, help='Description, in quotes')
    parser.add_argument('--inputmaskpath', default=None, help='Directory of input masks')
    parser.add_argument('--arguments', nargs='+', default={},
                        help='Additional operation/plugin arguments e.g. rotation 60 ')
    parser.add_argument('--continueWithWarning', action='store_true', help='Tag to ignore version warning')
    parser.add_argument('--jpg', action='store_true', help='Create JPEG and copy metadata from base')
    parser.add_argument('--projectDescription', default=None, help='Description to set to all projects')
    parser.add_argument('--technicalSummary', default=None, help='Technical Summary to set to all projects')
    parser.add_argument('--username', default=None, help='Username for projects')
    parser.add_argument('--organization', default=None, help='User\'s Organization')
    parser.add_argument('--semanticRestaging', action='store_true',
                        help='Include this argument if this project will include semantic restaging')
    parser.add_argument('--semanticRepurposing', action='store_true',
                        help='Include this argument if this project will include semantic repurposing')
    parser.add_argument('--semanticEventFabrication', action='store_true',
                        help='Include this argument if this project will include semantic event fabrication')
    parser.add_argument('--imageReformatting', action='store_true',
                        help='Include this argument if this project will include image reformatting.')
    parser.add_argument('--s3', default=None, help='S3 Bucket/Path to upload projects to')
    parser.add_argument('--graph', action='store_true', help='Output Summary Graph')
    parser.add_argument('--threads', default='1', help='Number of Threads')
    parser.add_argument('--loglevel', required=False, help='log level')

    args = parser.parse_args()

    props = parse_properties(args.sourceDir, args.endDir, args.plugin, args.specification,
                             projectdescription=args.projectDescription,
                             technicalsummary=args.technicalSummary, username=args.username,
                             organization=args.organization,
                             semanticrestaging=args.semanticRestaging, semanticrepurposing=args.semanticRepurposing,
                             semanticrefabrication=args.semanticEventFabrication,
                             imagereformat=args.imageReformatting)

    setPwdX(CustomPwdX(args.username))
    maskgen.plugins.loadPlugins()
    if args.plugins:
        for plugin in maskgen.plugins.loadPlugins().keys():
            if args.plugin is not None and plugin != args.plugin:
                continue
            print ('---------------------------------------')
            print (plugin)
            op = maskgen.plugins.getOperation(plugin)
            if 'arguments' not in op or op['arguments'] is None:
                continue
            print ('Arguments:')
            argsProcessed = set()
            for name, definition in op['arguments'].iteritems():
                argsProcessed.add(name)
                vals = (' of ' + ','.join([str(v) for v in definition['values']])) if definition[
                                                                                          'type'] == 'list' else ''
                print ('  {}: {}{} [ {} ]'.format(name, definition['type'], vals,
                                                 definition['description'] if 'description' in definition else ''))
            opdef = getOperation(op['name'], fake=True)
            for name, definition in opdef.mandatoryparameters.iteritems():
                if name not in argsProcessed:
                    vals = (' of ' + ','.join([str(v) for v in definition['values']])) if definition[
                                                                                              'type'] == 'list' else ''
                    print ('  {}: {}{} [ {} ]'.format(name, definition['type'], vals,
                                                     definition['description'] if 'description' in definition else ''))
            for name, definition in opdef.optionalparameters.iteritems():
                if name not in argsProcessed:
                    vals = (' of ' + ','.join([str(v) for v in definition['values']])) if definition[
                                                                                              'type'] == 'list' else ''
                    print ('  {}*: {}{} [ {} ]'.format(name, definition['type'], vals,
                                                      definition['description'].encode('ascii',
                                                                                       errors='ignore') if 'description' in definition else ''))
        return

    elif args.specification:
        if args.projects is None:
            print ('projects is required')
            sys.exit(-1)
        processSpecification(args.specification, args.extensionRules, args.projects, completeFile=args.completeFile,
                             outputGraph=args.graph, threads=int(args.threads), loglevel=args.loglevel)
    # perform the specified operation
    elif args.plugin:
        if args.projects is None:
            print ('projects is required')
            sys.exit(-1)
        opDef = maskgen.plugins.getOperation(args.plugin)
        if opDef is not None:
            op = getOperation(opDef['name'])
            if op is None:
                print ('Invalid Operation definition {} for plugin.  Plugin is an invalid state.'.format(args.op))
                sys.exit(-1)
        additionalArgs = args_to_map(args.arguments, op)
        if 'arguments' in opDef and opDef['arguments'] is not None:
            for k, v in opDef['arguments'].iteritems():
                if v is not None and 'defaultvalue' in v and v['defaultvalue'] is not None \
                        and k not in additionalArgs:
                    additionalArgs[k] = v['defaultvalue']

        additionalArgs = check_additional_args(additionalArgs, op, args.continueWithWarning)

        print ('Performing plugin operation ' + args.plugin + '...')
        process_plugin(args.sourceDir, args.projects, args.plugin, props, additionalArgs)
    elif args.sourceDir:
        op = getOperation(args.op)
        if args.projects is None:
            print ('projects is required')
            sys.exit(-1)
        if op is None:
            print ('Invalid Operation {}'.format(args.op))
            sys.exit(-1)
        additionalArgs = args_to_map(args.arguments, op)
        additionalArgs = {} if args.op is None else check_additional_args(additionalArgs, op, args.continueWithWarning)
        if args.op:
            print ('Adding operation ' + args.op + '...')
        process(args.sourceDir, args.endDir, args.projects, args.op, args.softwareName,
                args.softwareVersion, args.description, args.inputmaskpath, additionalArgs,
                props)
    if args.jpg:
        print ('Performing JPEG save & copying metadata from base...')
        process_jpg(args.projects)

    # bulk export to s3
    if args.s3:
        bulk_export.upload_projects(args.s3, args.projects)


if __name__ == '__main__':
    main()
