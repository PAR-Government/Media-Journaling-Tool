from __future__ import print_function
import argparse
import os
import maskgen.scenario_model
from maskgen.tool_set import *
from maskgen import video_tools
import tempfile
from maskgen.scenario_model import ImageProjectModel
from maskgen.image_graph import extract_archive
from maskgen.graph_rules import processProjectProperties
from maskgen.batch import BatchProcessor, pick_projects
import hashlib
import shutil
import sys
import csv
import time
from functools import partial
from maskgen import plugins



def reproduceMask(scModel):
    """
    Rebuild all edge masks
    :param scModel: scenario model
    :return:
    """
    for edge in scModel.getGraph().get_edges():
        scModel.select(edge)
        scModel.reproduceMask()
    print ('Updated masks in project: ' + str(scModel.getName()))


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

mod_functions=globals()
def getFunction(name, function_mappings={}):
    if name is None:
        return None
    import importlib
    if name in function_mappings:
        return function_mappings[name]
    elif name in mod_functions:
        function_mappings[name] = mod_functions[name]
        return function_mappings[name]
    else:
        mod_name, func_name = name.rsplit('.', 1)
        try:
            mod = importlib.import_module(mod_name)
            func = getattr(mod, func_name)
            function_mappings[name] = func
            return func
        except Exception as e:
            logging.getLogger('maskgen').error('Unable to load rule {}: {}'.format(name,str(e)))
            raise e

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

def isSuccessor(scModel, successors, node, ops):
    """
      :param scModel:
      :return:
      @type successors: list of str
      @type scModel: ImageProjectModel
      """
    for successor in successors:
        edge = scModel.getGraph().get_edge(node,successor)
        if edge['op'] not in ops:
            return False
    return True

def missingVideo(scModel):
    import copy
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        successors = scModel.getGraph().successors(edge[1])
        predecessors = scModel.getGraph().predecessors(edge[1])
        if currentLink['op'] == 'AddAudioSample':
            sourceim, source = scModel.getGraph().get_image(edge[0])
            im, dest = scModel.getGraph().get_image(edge[1])
            sourcemetadata = video_tools.getMeta(source,show_streams=True)[0]
            destmetadata = video_tools.getMeta(dest,show_streams=True)[0]
            if len(sourcemetadata) > 0:
                sourcevidcount = len([idx for idx, val in enumerate(sourcemetadata) if val['codec_type'] != 'audio'])
            if len(destmetadata) > 0:
                destvidcount = len([x for x in (idx for idx, val in enumerate(destmetadata) if val['codec_type'] != 'audio')])
            if sourcevidcount != destvidcount:
                if not isSuccessor(scModel, successors, edge[1], ['AntiForensicCopyExif', 'OutputMP4', 'Donor']):
                    raise ValueError('Cannot correct AddAudioSample for edge {} to {} due to successor node'.format(
                        edge[0], edge[1]
                    ))
                predecessors = [pred for pred in predecessors if pred != edge[0]]
                if len(predecessors) == 0:
                    donor = scModel.getBaseNode(edge[1])
                else:
                    donor = predecessors[0]
                args= dict() if 'arguments' not  in currentLink else copy.copy(currentLink['arguments'])
                args['donor'] = donor
                plugins.callPlugin('OverwriteAudioStream',sourceim,source,dest,donor=donor)

def recompressAsVideo(scModel):
    """
    :param scModel:
    :return:
    @type scModel: maskgen.scenario_model.ImageProjectModel
    """
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        successors = scModel.getGraph().successors(edge[1])
        predecessors = scModel.getGraph().predecessors(edge[1])
        # should we consider video nodes just to be sure?
        #finalNode = scModel.getGraph().get_node(edge[1])
        if currentLink['op'] == 'AntiForensicCopyExif' and \
            len(successors) == 0 and \
            currentLink['softwareName'].lower() == 'ffmpeg':
            predecessors = [pred for pred in predecessors if pred != edge[0]]
            if len (predecessors) == 0:
                donor = scModel.getBaseNode(edge[1])
            else:
                donor = predecessors[0]
            scModel.selectImage(edge[1])
            scModel.remove()
            scModel.selectImage(edge[0])
            scModel.imageFromPlugin('CompressAsVideo',donor=donor)


def perform_update(project,args, functions,  tempdir):
    scModel = maskgen.scenario_model.ImageProjectModel(project)
    print ('User: ' + scModel.getGraph().getDataItem('username'))
    validator = scModel.getProjectData('validatedby')
    if not args.validate:
        if validator is  not None:
            setPwdX(CustomPwdX(validator))
        else:
            setPwdX(CustomPwdX(scModel.getGraph().getDataItem('username')))
    for function in functions:
        function(scModel)
    if args.validate:
        scModel.set_validation_properties('yes', get_username(), 'QA redone via Batch Updater')
    scModel.save()
    if args.updategraph:
        if os.path.exists(os.path.join(scModel.get_dir(),'_overview_.png')):
            return
    if args.export:
        error_list = scModel.exporttos3(args.uploadfolder, tempdir)
        if len(error_list) > 0:
            for err in error_list:
                print (err)
            raise ValueError('Export Failed')
    return scModel.validate()

def fetchfromS3(dir, location, file):
    import boto3
    BUCKET = location.split('/')[0].strip()
    DIR = location[location.find('/') + 1:].strip() +'/'
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(BUCKET)
    my_bucket.download_file(DIR + file, os.path.join(dir, file))

def processProject(args, functions, file_to_process):
    """

    :param args:
    :param functions:
    :param file_to_process:
    :return:
    @type file_to_process : str
    """
    if not file_to_process.endswith('tgz') and os.path.exists(os.path.join(args.tempfolder,file_to_process)):
        dir = os.path.join(args.tempfolder,file_to_process)
        fetch = False
    else:
        dir = tempfile.mkdtemp(dir=args.tempfolder) if args.tempfolder else tempfile.mkdtemp()
        fetch = True
    try:
        if fetch:
            fetchfromS3(dir, args.downloadfolder,file_to_process)
            extract_archive(os.path.join(dir, file_to_process), dir)
        for project in pick_projects(dir):
            perform_update(project, args,functions, dir)
    finally:
        if fetch:
            shutil.rmtree(dir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f',  '--file', required=True, help='File of projects')
    parser.add_argument('-df', '--threads', required=True, help='Download folder')
    parser.add_argument('-ug', '--updategraph', required=False, help='Upload Graph',action='store_true')
    parser.add_argument('-uf', '--uploadfolder', required=True, help='Upload folder')
    parser.add_argument('-v',  '--validate', required=False, help='QA',action='store_true')
    parser.add_argument('-tf', '--tempfolder', required=False, help='Temp Holder')
    parser.add_argument('-e',  '--functions', required=False, help='List of function')
    parser.add_argument('-cf', '--completefile', required=True, help='Projects to Completed')
    parser.add_argument('-x', '--export', required=False, action='store_true', help='Export Results')
    args = parser.parse_args()

    functions_map = {}
    functions = []
    if args.functions is not None:
        functions = [getFunction(name, function_mappings=functions_map) for name in args.functions.split(',')]

    with open(args.file, 'r') as input_file:
        files_to_process = input_file.readlines()
    files_to_process = [x.strip() for x in files_to_process]

    processor = BatchProcessor(args.completefile,files_to_process)
    func = partial(processProject,args,functions)
    processor.process(func)

if __name__ == '__main__':
    main()
