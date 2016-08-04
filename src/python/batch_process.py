"""
Bulk Image Journal Processing
"""
import argparse
import sys
from software_loader import *
import scenario_model
import tool_set
import bulk_export

def find_corresponding_image(image, imageList):
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
    ext = ('.jpg', '.tif', '.png')
    return [i for i in os.listdir(fileList) if i.endswith(ext)]


def process(sourceDir, endDir, projectDir, op, category, software, version, descr, inputMaskPath, rotation):
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
    :param rotation: Image rotation angle. Optional.
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
        opDetails = scenario_model.Modification(op, descr, category=category, inputmaskname=maskIm,
                                                arguments={'rotation': rotation})
        softwareDetails = Software(software, version)
        position = ((startNode['xpos'] + 50 if startNode.has_key('xpos') else
                     80), (startNode['ypos'] + 50 if startNode.has_key('ypos') else 200))

        # create link
        sm.selectImage(nodes[-1])
        sm.addNextImage(eImg, tool_set.openImage(eImg), mod=opDetails, software=softwareDetails,
                        sendNotifications=False, position=position)
        sm.save()

        print 'Completed project (' + str(processNo) + '/' + str(total) + '): ' + nodes[0]
        processNo += 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sourceDir',                                  help='Directory of starting images')
    parser.add_argument('--endDir',              default=None,          help='Directory of manipulated images')
    parser.add_argument('--projects',                                   help='Projects directory')
    parser.add_argument('--op',                                         help='Operation Name')
    parser.add_argument('--softwareName',                               help='Software Name')
    parser.add_argument('--softwareVersion',                            help='Software Version')
    parser.add_argument('--description',         default=None,          help='Description, in quotes')   # optional
    parser.add_argument('--inputmaskpath',       default=None,          help='Directory of input masks') # optional
    parser.add_argument('--rotation',            default=0,             help='rotation angle')           # optional
    parser.add_argument('--continueWithWarning', action='store_true',   help='Tag to ignore version warning') # optional
    parser.add_argument('--s3',                  default=None,          help='S3 Bucket/Path to upload projects to') # optional
    args = parser.parse_args()

    ops = loadOperations("operations.json")
    soft = loadSoftware("software.csv")

    if (ops != getOperations() or soft != getSoftwareSet()) and not args.continueWithWarning:
        sys.exit('Invalid operation file. Please update.')

    if not getOperation(args.op) and not args.continueWithWarning:
        print 'Invalid operation: ' + args.op
        print 'Reference the operations.json file for accepted operations.'
        sys.exit(0)

    if not validateSoftware(args.softwareName, args.softwareVersion) and not args.continueWithWarning:
        print 'Invalid software/version: ' + args.softwareName + ' ' + args.softwareVersion
        print 'Reference the software.csv file for accepted names and versions. They are case-sensitive.'
        sys.exit(0)

    category = ops[args.op].category

    process(args.sourceDir, args.endDir, args.projects, args.op, category, args.softwareName,
            args.softwareVersion, args.description, args.inputmaskpath, args.rotation)

    if args.s3:
        bulk_export.upload_projects(args.s3, args.projects)

if __name__ == '__main__':
    main()