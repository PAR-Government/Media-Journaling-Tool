"""
Bulk Image Journal Processing
"""
import argparse
import sys
from software_loader import *
import scenario_model
import tool_set

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
    prjDir = dir + '/' + image
    jsonPath = prjDir + '/' + image + '.json'

    # create project/json directory if doesn't exist
    if not os.path.exists(prjDir):
        os.makedirs(prjDir)
    return jsonPath

def create_image_list(fileList):
    ext = ('.jpg', '.tif', '.png')
    return [i for i in os.listdir(fileList) if i.endswith(ext)]


def process(sourceDir, endDir, projectDir, op, category, software, version, descr, inputMaskPath):
    """
    Perform the bulk journaling
    :param sourceDir: Directory of source images
    :param endDir: Directory of manipulated images (1 manipulation stage)
    :param projectDir: Directory for projects to be placed
    :param op: Operation performed between source and ending dir
    :param category: Operation category
    :param software: Manipulation software used
    :param version: Version of manipulation software
    :param descr: Optional description of manipulation
    :param inputMaskPath: Optional directory of input masks
    :return: None
    """

    # create/locate initial directories for start, end, project, and input masks
    startingImages = create_image_list(sourceDir)
    endingImages = create_image_list(endDir)
    if inputMaskPath:
        inputMaskImages = create_image_list(inputMaskPath)
    else:
        inputMaskImages = None
    total = len(startingImages)
    processNo = 1

    # begin looping through the different projects
    for sImg in startingImages:
        sImgName = sImg.split('.')[:-1]
        eImg = (endDir + '/' + find_corresponding_image(sImgName, endingImages)).replace('\\','/')
        if inputMaskPath:
            maskIm = (inputMaskPath + '/' + find_corresponding_image(sImgName, inputMaskImages)).replace('\\','/')
        else:
            maskIm = None

        # create project directory if doesn't exist
        project = find_json_path(sImgName, projectDir).replace('\\','/')

        opDetails = scenario_model.Modification(op, descr, category=category, inputmaskpathname=maskIm)
        softwareDetails = Software(software, version)

        sm = scenario_model.ProjectModel(project)

        sm.addImage(sourceDir + '/' + sImg)
        startNode = sm.G.get_node(sImgName)
        position = ((startNode['xpos'] + 50 if startNode.has_key('xpos') else
                      80), (startNode['ypos'] + 50 if startNode.has_key('ypos') else 200))

        sm.selectImage(sImgName)
        sm.addNextImage(eImg, tool_set.openImage(eImg), mod=opDetails, software=softwareDetails,
                        sendNotifications=False, position=position)
        sm.save()

        print 'Completed project (' + str(processNo) + '/' + str(total) + '): ' + sImgName
        processNo += 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sourceDir',                                  help='Directory of starting images')
    parser.add_argument('--endDir',                                     help='Directory of manipulated images')
    parser.add_argument('--projects',                                   help='Projects directory')
    parser.add_argument('--op',                                         help='Operation Name')
    parser.add_argument('--softwareName',                               help='Software Name')
    parser.add_argument('--softwareVersion',                            help='Software Version')
    parser.add_argument('--description',         default=None,          help='Description, in quotes')   # optional
    parser.add_argument('--inputmaskpath',       default=None,          help='Directory of input masks') # optional
    parser.add_argument('--rotation',            default=None,          help='rotation angle')           # optional
    parser.add_argument('--continueWithWarning', action='store_true',   help='Tag to ignore version warning')
    args = parser.parse_args()

    ops = loadOperations("operations.csv")
    soft = loadSoftware("software.csv")

    if (ops != getOperations() or soft != getSoftwareSet()) and not args.continueWithWarning:
        sys.exit('Invalid operation file. Please update.')

    category = ops[args.op][0]
    process(args.sourceDir, args.endDir, args.projects, args.op, category,
            args.softwareName, args.softwareVersion, args.description, args.inputmaskpath)

if __name__ == '__main__':
    main()