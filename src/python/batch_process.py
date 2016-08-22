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

def check_one_function(args):
    """
    Error-checking function that ensures only 1 operation is performed
    """
    sum = bool(args.plugin) + bool(args.sourceDir) + bool(args.jpg)

    if sum > 1:
        print 'ERROR: Can only specify one of the following: '
        print '    --sourceDir: creates project/adds specified operation to project'
        print '    --plugin (performs the specified plugin'
        print '    --jpg: creates jpg image from last node and copies metadata from base'
        sys.exit(0)
    elif sum == 0:
        print 'ERROR: Must specify exactly 1 of the following: '
        print '    --sourceDir: creates project/adds specified operation to project'
        print '    --plugin (performs the specified plugin'
        print '    --jpg: creates jpg image from last node and copies metadata from base'
        sys.exit(0)

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


def process(sourceDir, endDir, projectDir, op, category, software, version, descr, inputMaskPath, additional):
    """
    Perform the bulk journaling. If no endDir is specified, it is assumed that the user wishes
    to add on to existing projects in projectDir.
    :param sourceDir: Directory of source images
    :param endDir: Directory of manipulated images (1 manipulation stage). Optional.
    :param projectDir: Directory for projects to be placed
    :param op: Operation performed between source and ending dir
    :param category: Operation category
    :param software: Manipulation software used
    :param version: Version of manipulation software
    :param descr: Description of manipulation. Optional
    :param inputMaskPath: Directory of input masks. Optional.
    :param additional: Dictionary of additional args ({rotation:90,...}). Optional.
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

        # find project dir
        if new:
            project = find_json_path(sImgName, projectDir)
        else:
            projectName = '_'.join(sImgName.split('_')[:-1])
            project = find_json_path(projectName, projectDir)

        # open the project
        sm = scenario_model.ProjectModel(project)
        if new:
            sm.addImage(os.path.join(sourceDir, sImg))
            eImg = os.path.join(endDir, find_corresponding_image(sImgName, endingImages))
        else:
            eImg = os.path.join(sourceDir, sImg)

        # find most recently placed node
        nodes = sm.G.get_nodes()
        nodes.sort()
        startNode = sm.G.get_node(nodes[-1])

        # prepare details for new link
        softwareDetails = Software(software, version)
        if additional:
            opDetails = scenario_model.Modification(op, descr, software=softwareDetails, inputMaskName=maskIm,
                                                    arguments=additional, automated='yes')
        else:
            opDetails = scenario_model.Modification(op, descr, software=softwareDetails, inputMaskName=maskIm,automated='yes')

        position = ((startNode['xpos'] + 50 if startNode.has_key('xpos') else
                     80), (startNode['ypos'] + 50 if startNode.has_key('ypos') else 200))

        # create link
        sm.selectImage(nodes[-1])
        sm.addNextImage(eImg, mod=opDetails,
                        sendNotifications=False, position=position)

        sm.save()

        print 'Completed project (' + str(processNo) + '/' + str(total) + '): ' + project
        processNo += 1


def process_plugin(projects, plugin):
    """
    Perform a plugin operation on all projects in directory
    :param projects: directory of projects
    :param plugin: plugin to perform
    :return: None
    """
    projectList = bulk_export.pick_dirs(projects)
    total = len(projectList)
    processNo = 1
    for project in projectList:
        sm = scenario_model.ProjectModel(project)
        nodes = sm.G.get_nodes()
        nodes.sort()
        sm.selectImage(nodes[-1])
        im, filename = sm.currentImage()
        plugins.loadPlugins()
        sm.imageFromPlugin(plugin, im, filename)
        sm.save()
        print 'Completed project (' + str(processNo) + '/' + str(total) + '): ' + project
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
        sm = scenario_model.ProjectModel(project)
        plugins.loadPlugins()
        op = group_operations.ToJPGGroupOperation(sm)
        op.performOp()
        sm.save()
        print 'Completed project (' + str(processNo) + '/' + str(total) + '): ' + project
        processNo += 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projects',                                   help='Projects directory')
    parser.add_argument('--plugin',              default=None,          help='Perform specified plugin operation')
    parser.add_argument('--sourceDir',           default=None,          help='Directory of starting images')
    parser.add_argument('--endDir',              default=None,          help='Directory of manipulated images')
    parser.add_argument('--op',                  default=None,          help='Operation Name')
    parser.add_argument('--softwareName',        default=None,          help='Software Name')
    parser.add_argument('--softwareVersion',     default=None,          help='Software Version')
    parser.add_argument('--description',         default=None,          help='Description, in quotes')
    parser.add_argument('--inputmaskpath',       default=None,          help='Directory of input masks')
    parser.add_argument('--additional',          default=None,          help='additional operation arguments, e.g. rotation')
    parser.add_argument('--continueWithWarning', action='store_true',   help='Tag to ignore version warning')
    parser.add_argument('--jpg',                 action='store_true',   help='Create JPEG and copy metadata from base')
    parser.add_argument('--s3',                  default=None,          help='S3 Bucket/Path to upload projects to')
    args = parser.parse_args()

    ops = loadOperations("operations.json")
    soft = loadSoftware("software.csv")

    # make sure only 1 operation per command
    check_one_function(args)

    # parse additional arguments (rotation, etc.)
    # http://stackoverflow.com/questions/6900955/python-convert-list-to-dictionary
    if args.additional:
        add = args.additional.split(' ')
        additionalArgs = dict(itertools.izip_longest(*[iter(add)] * 2, fillvalue=""))
    else:
        additionalArgs = args.additional

    # perform the specified operation
    if args.plugin:
        print 'Performing plugin operation ' + args.plugin + ' assuming sourceDir as donor.'
        process_plugin(args.projects, args.plugin)
    elif args.jpg:
        print 'Performing JPEG save & copying metadata from base.'
        process_jpg(args.projects)
    else:
        check_ops(ops, soft, args)
        category = ops[args.op].category
        process(args.sourceDir, args.endDir, args.projects, args.op, category, args.softwareName,
                args.softwareVersion, args.description, args.inputmaskpath, additionalArgs)

    if args.s3:
        bulk_export.upload_projects(args.s3, args.projects)

if __name__ == '__main__':
    main()
