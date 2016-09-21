"""
Bulk Image Journal Processing
"""
import argparse
import sys
import itertools
from software_loader import *
import scenario_model
import tool_set
import bulk_export
import group_operations
import plugins
import software_loader


def check_ops(ops, soft, args):
    """
    Error-checking function that ensures operations and software are valid.
    """
    if (ops != getOperations() or soft != getSoftwareSet()) and not args.continueWithWarning:
        print 'ERROR: Invalid operation file. Please update.'
        sys.exit(0)

    if not getOperation(args.op) and not args.continueWithWarning:
        print 'ERROR: Invalid operation: ' + args.op
        print 'Reference the operations.json file for accepted operations.'
        sys.exit(0)

    if not validateSoftware(args.softwareName, args.softwareVersion) and not args.continueWithWarning:
        print 'ERROR: Invalid software/version: ' + args.softwareName + ' ' + args.softwareVersion
        print 'Reference the software.csv file for accepted names and versions. They are case-sensitive.'
        sys.exit(0)

    return

def check_additional_args(additionalArgs, op):
    """
    Parse additional arguments (rotation, etc.) and validate
    :param additionalArgs: user input list of additional parameters e.g. [rotation, 60...]
    :param op: operation object (use software_loader.getOperation('operationname')
    :return: dictionary containing parsed arguments e.g. {rotation: 60}
    """
    # parse additional arguments (rotation, etc.)
    # http://stackoverflow.com/questions/6900955/python-convert-list-to-dictionary
    if additionalArgs != {}:
        parsedArgs = dict(itertools.izip_longest(*[iter(additionalArgs)] * 2, fillvalue=""))
        for key in parsedArgs:
            parsedArgs[key] = tool_set.validateAndConvertTypedValue(key, parsedArgs[key], op)
    else:
        parsedArgs = additionalArgs
    for key in op.mandatoryparameters.keys():
        if key not in parsedArgs.keys():
            sys.exit('Missing required additional argument: ' + key)
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
    ext = ('.jpg', '.tif', '.png')
    return [i for i in os.listdir(fileList) if i.endswith(ext)]

def generate_composites(projectsDir):
    projects = bulk_export.pick_dirs(projectsDir)
    for prj in projects:
        sm = scenario_model.ImageProjectModel(prj)
        sm.constructComposites()
        sm.save()


def process(sourceDir, endDir, projectDir, op, software, version, opDescr, inputMaskPath, additional,
            prjDescr, techSummary, username):
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
    :param additional: Dictionary of additional args ({rotation:90,...})
    :param prjDescr: project description (str)
    :param techSummary: project's technical summary (str)
    :param username: project username
    :return: None
    """

    startingImages = create_image_list(sourceDir)

    # Decide what to do with input (create new or add)
    if endDir:
        endingImages = create_image_list(endDir)
        new = True
        print 'Creating new projects...'
    else:
        endingImages = None
        new = False
        print 'Adding to existing projects...'

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
        sm = scenario_model.ImageProjectModel(project)
        if new:
            sm.addImage(os.path.join(sourceDir, sImg))
            lastNodeName = sImgName
            sm.setProjectData('projectdescription', prjDescr)
            sm.setProjectData('technicalsummary', techSummary)
            if username:
                sm.setProjectData('username', username)
            eImg = os.path.join(endDir, find_corresponding_image(sImgName, endingImages))
        else:
            eImg = os.path.join(sourceDir, sImg)
            lastNodeName = sm.G.get_edges()[-1][-1]

        lastNode = sm.G.get_node(lastNodeName)

        # prepare details for new link
        softwareDetails = Software(software, version)
        if additional:
            opDetails = scenario_model.Modification(op, opDescr, software=softwareDetails, inputMaskName=maskIm,
                                                    arguments=additional, automated='yes')
        else:
            opDetails = scenario_model.Modification(op, opDescr, software=softwareDetails, inputMaskName=maskIm,automated='yes')

        position = ((lastNode['xpos'] + 50 if lastNode.has_key('xpos') else
                     80), (lastNode['ypos'] + 50 if lastNode.has_key('ypos') else 200))

        # create link
        sm.selectImage(lastNodeName)
        sm.addNextImage(eImg, mod=opDetails,
                        sendNotifications=False, position=position)
        sm.save()

        print 'Completed project (' + str(processNo) + '/' + str(total) + '): ' + project
        processNo += 1


def process_plugin(sourceDir, projects, plugin, prjDescr, techSummary, username):
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
        iterator = bulk_export.pick_dirs(projects)

    total = len(iterator)
    processNo = 1
    for i in iterator:
        if new:
            sImgName = ''.join(i.split('.')[:-1])
            project = find_json_path(sImgName, projects)
            sm = scenario_model.ImageProjectModel(project)
            sm.setProjectData('projectdescription', prjDescr)
            sm.setProjectData('technicalsummary', techSummary)
            if username:
                sm.setProjectData('username', username)
            sm.addImage(os.path.join(sourceDir, i))
            lastNode = sImgName
        else:
            sm = scenario_model.ImageProjectModel(i)
            lastNode = sm.G.get_edges()[-1][-1]
        sm.selectImage(lastNode)
        im, filename = sm.currentImage()
        plugins.loadPlugins()
        sm.imageFromPlugin(plugin, im, filename)
        sm.save()
        print 'Completed project (' + str(processNo) + '/' + str(total) + '): ' + i
        processNo += 1

def process_jpg(projects):
    """
    Save image as JPEG using the q tables of the base image, and copy exif from base for all projects in directory.
    :param projects: directory of projects
    :return: None
    """
    projectList = bulk_export.pick_dirs(projects)
    total = len(projectList)
    processNo = 1
    for project in projectList:
        sm = scenario_model.ImageProjectModel(project)
        plugins.loadPlugins()
        op = group_operations.ToJPGGroupOperation(sm)
        op.performOp()
        sm.save()
        print 'Completed project (' + str(processNo) + '/' + str(total) + '): ' + project
        processNo += 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projects',             required=True,         help='Projects directory')
    parser.add_argument('--plugin',               default=None,          help='Perform specified plugin operation')
    parser.add_argument('--sourceDir',            default=None,          help='Directory of starting images')
    parser.add_argument('--endDir',               default=None,          help='Directory of manipulated images')
    parser.add_argument('--op',                   default=None,          help='Operation Name')
    parser.add_argument('--softwareName',         default=None,          help='Software Name')
    parser.add_argument('--softwareVersion',      default=None,          help='Software Version')
    parser.add_argument('--description',          default=None,          help='Description, in quotes')
    parser.add_argument('--inputmaskpath',        default=None,          help='Directory of input masks')
    parser.add_argument('--additional', nargs='+',default={},            help='additional operation arguments, e.g. rotation')
    parser.add_argument('--continueWithWarning',  action='store_true',   help='Tag to ignore version warning')
    parser.add_argument('--jpg',                  action='store_true',   help='Create JPEG and copy metadata from base')
    parser.add_argument('--projectDescription',   default=None,          help='Description to set to all projects')
    parser.add_argument('--technicalSummary',     default=None,          help='Technical Summary to set to all projects')
    parser.add_argument('--username',             default=None,          help='Username for projects')
    parser.add_argument('--s3',                   default=None,          help='S3 Bucket/Path to upload projects to')
    args = parser.parse_args()

    ops = loadOperations("operations.json")
    soft = loadSoftware("software.csv")

    # perform the specified operation
    if args.plugin:
        print 'Performing plugin operation ' + args.plugin + '...'
        process_plugin(args.sourceDir, args.projects, args.plugin, args.projectDescription,
                       args.technicalSummary, args.username)
    elif args.sourceDir:
        check_ops(ops, soft, args)
        additionalArgs = check_additional_args(args.additional, software_loader.getOperation(args.op))
        process(args.sourceDir, args.endDir, args.projects, args.op, args.softwareName,
                args.softwareVersion, args.description, args.inputmaskpath, additionalArgs,
                args.projectDescription, args.technicalSummary, args.username)
    if args.jpg:
        print 'Performing JPEG save & copying metadata from base...'
        process_jpg(args.projects)

    # generate composites
    generate_composites(args.projects)

    # bulk export to s3
    if args.s3:
        bulk_export.upload_projects(args.s3, args.projects)

if __name__ == '__main__':
    main()
