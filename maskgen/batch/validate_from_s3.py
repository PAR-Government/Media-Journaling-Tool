import argparse
import os
import maskgen.scenario_model
from maskgen.tool_set import *
import tempfile
from maskgen.image_graph import extract_archive
from maskgen.graph_rules import processProjectProperties
from maskgen.batch import BatchProcessor, pick_projects
import hashlib
import shutil
import sys
import csv
import time
from functools import partial


def rebuild_masks(scModel):
    """
    Rebuild all edge masks
    :param scModel: scenario model
    :return:
    """
    for edge in scModel.getGraph().get_edges():
        scModel.select(edge)
        scModel.reproduceMask()
    print 'Updated masks in project: ' + str(scModel.getName())


def select_region(imfile, prev):
    im = openImage(imfile)
    if im.mode == 'RGBA' or im.mode == 'LA':
        return imfile
    else:
        if not os.path.exists(prev):
            pos = prev.rfind('.')
            mod_filename = prev[0:pos] + prev[pos:].lower()
            if os.path.exists(mod_filename):
                prev = mod_filename
        prevIm = Image.open(prev)
        if im.mode == 'L' and set(im.getdata()).issubset({0, 1, 255}) and not isRGBA(prevIm):
            rgba = prevIm.convert('RGBA')
            bw = im.point(lambda x: 1 if x > 0 else 0, 'F')
            rgbaarr = np.asarray(rgba)
            bwa = np.asarray(bw)

            prod = np.multiply(bw, rgbaarr[3,:,:])

            newIm = np.array([rgbaarr[0,:,:], rgbaarr[1,:,:], rgbaarr[2,:,:], prod])
            newImPIL = Image.fromarray(newIm, 'RGBA')
            newImPIL.save(imfile)
            return imfile
    return imfile

def isRGBA(im):
    return im.mode == 'RGBA'

def replace_oldops(scModel):
    """
    Replace selected operations
    :param scModel: Opened project model
    :return: None. Updates JSON.
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
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            currentLink['recordMaskInComposite'] = 'true'
            currentLink['arguments']['purpose'] = 'heal'

def update_rotation(scModel):
    """
    Add rotation parameter to OutputPNG and OutputTIFF operations
    :param scModel: Opened project model
    :param project: Project JSON file
    :return: None. Updates JSON.
    """
    rotateOps = ['OutputPng', 'OutputTif']
    projectDir = scModel.getGraph().dir
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        if currentLink['op'] in rotateOps:
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            if 'Image Rotated' in currentLink['arguments']:
                continue
            change = edge['shape change'] if 'shape change' in edge else None
            if change and change != '(0,0)':
                currentLink['arguments']['Image Rotated'] = 'yes'
            elif change and change == '(0,0)':
                currentLink['arguments']['Image Rotated'] = 'no'
            else:
                startFile = scModel.getGraph().get_node(edge[0])['file']
                endFile = scModel.getGraph().get_node(edge[1])['file']
                im1 = Image.open(os.path.join(projectDir, startFile))
                im2 = Image.open(os.path.join(projectDir, endFile))
                if im1.size != im2.size:
                    currentLink['arguments']['Image Rotated'] = 'yes'
                else:
                    currentLink['arguments']['Image Rotated'] = 'no'


def validate_by(scModel, person):
    scModel.setProjectData('validation', 'yes')
    scModel.setProjectData('validatedby', person)
    scModel.setProjectData('validationdate', time.strftime("%m/%d/%Y"))
    scModel.save()

def toCSV(scModel,args):
    scModel.assignColors()
    processProjectProperties(scModel)
    scModel.toCSV(os.path.join(scModel.get_dir(),'colors.csv'))
    scModel.export(args.tempfolder,include=['colors.csv'])

def perform_update(project,args,   tempdir):
    scModel = maskgen.scenario_model.ImageProjectModel(project)
    print 'User: ' + scModel.getGraph().getDataItem('username')
    validator = scModel.getProjectData('validatedby')
    if not args.validate:
        if validator is  not None:
            setPwdX(CustomPwdX(validator))
        else:
            setPwdX(CustomPwdX(scModel.getGraph().getDataItem('username')))

    if args.composites:
        toCSV(scModel)
    if args.redomasks:
        rebuild_masks(scModel)
    if args.validate:
        scModel.set_validation_properties('yes', get_username(), 'QA redone via Batch Updater')
    scModel.save()
    if args.updategraph:
        if os.path.exists(os.path.join(scModel.get_dir(),'_overview_.png')):
            return
    error_list = scModel.exporttos3(args.uploadfolder, tempdir)
    if len(error_list) > 0:
        for err in error_list:
            print err
        raise ValueError('Export Failed')
    return scModel.validate()

def fetchfromS3(dir, location, file):
    import boto3
    BUCKET = location.split('/')[0].strip()
    DIR = location[location.find('/') + 1:].strip() +'/'
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(BUCKET)
    my_bucket.download_file(DIR + file, os.path.join(dir, file))

def processProject(args, file_to_process):
    dir = tempfile.mkdtemp(dir=args.tempfolder) if args.tempfolder else tempfile.mkdtemp()
    try:
        fetchfromS3(args.downloadfolder,file_to_process)
        extract_archive(os.path.join(dir, file_to_process), dir)
        for project in pick_projects(dir):
            perform_update(project, args, dir)
    finally:
        shutil.rmtree(dir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f',  '--file', required=True, help='File of projects')
    parser.add_argument('-df', '--downloadfolder', required=True, help='Download folder')
    parser.add_argument('-ug', '--updategraph', required=False, help='Upload Graph',action='store_true')
    parser.add_argument('-uf', '--uploadfolder', required=True, help='Upload folder')
    parser.add_argument('-c',  '--composites', help='Reconstruct composite images',action='store_true')
    parser.add_argument('-v',  '--validate', required=False, help='QA',action='store_true')
    parser.add_argument('-tf', '--tempfolder', required=False, help='Temp Holder')
    parser.add_argument('-rc', '--redomasks', help='Rebuild link masks',action='store_true')
    parser.add_argument('-cf', '--completefile', required=True, help='Projects to Completed')
    args = parser.parse_args()
    maskgen.tool_set.set_logging()

    with open(args.file, 'r') as input_file:
        files_to_process = input_file.readlines()
    files_to_process = [x.strip() for x in files_to_process]

    processor = BatchProcessor(args.completefile,files_to_process)
    func = partial(processProject,args)
    processor.process(func)

if __name__ == '__main__':
    main()
