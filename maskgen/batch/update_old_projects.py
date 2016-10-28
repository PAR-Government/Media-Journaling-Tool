import argparse
import os
import json
import cv2
import numpy as np
from PIL import Image
import maskgen.scenario_model
from maskgen.tool_set import *
import bulk_export
import tempfile
from maskgen.image_graph import extract_archive
from maskgen.graph_rules import processProjectProperties
from maskgen.group_operations import CopyCompressionAndExifGroupOperation
from maskgen.software_loader import Software,loadOperations,loadProjectProperties,loadSoftware
from maskgen.plugins import loadPlugins
import hashlib
import shutil
import csv


def label_project_nodes(scModel):
    """
    Labels all nodes on a project
    :param scModel: scenario model
    """
    p = scModel.getNodeNames()
    for node in p:
        scModel.labelNodes(node)
    #print 'Completed label_project_nodes'

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

def rename_donorsandbase(scModel,updatedir):
    """
    Rename donor images with MD5
    :param scModel: scenario model
    :return:
    """
    base_count = 0
    for node in scModel.getNodeNames():
        nodeData = scModel.getGraph().get_node(node)
        if len(scModel.getGraph().predecessors(node)) == 0 and \
            len(scModel.getGraph().successors(node)) == 0:
            scModel.getGraph().remove(node)
            continue
        if nodeData['nodetype'] in ['donor','base']:
            base_count += 1 if nodeData['nodetype'] == 'base' else 0
            file_path_name = os.path.join(scModel.get_dir(), nodeData['file'])
            with open(file_path_name, 'rb') as fp:
                md5 = hashlib.md5(fp.read()).hexdigest()
            suffix = nodeData['file'][nodeData['file'].rfind('.'):]
            new_file_name = md5 + suffix
            fullname =  os.path.join(scModel.get_dir(), new_file_name)
            if not os.path.exists(fullname):
                os.rename(file_path_name, fullname)
                nodeData['file'] = new_file_name
                shutil.copy(os.path.join(scModel.get_dir(),new_file_name), updatedir)
                print 'rename ' + file_path_name + ' to ' + fullname
        if base_count > 1:
            raise ValueError('Only one base image allowed per project')
    #print 'Completed rename_donors'


def update_photoshop_version(scModel):
    """
    Replaces photoshop CC16.16 with CC15.5.0
    :param scModel: Project model to be updated
    :return: None. Updates scModel.
    """
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        if currentLink['softwareName'] == 'Adobe Photoshop' and currentLink['softwareVersion'] == 'CC16.16':
            currentLink['version'] = 'CC15.5.0'
    #print 'Completed update_photoshop_version'

def check_pasteduplicate(scModel):
    """
    Update paste duplicate to have donor
    :param scModel: the project model to be updated
    :param project: project JSON file
    :return: None. Updates scModel.
    """
    projectDir = scModel.getGraph().dir
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        if currentLink['op'] == 'PasteDuplicate':
            if currentLink['inputmaskname'] is None:
                return 'PasteDuplicate Replacement Error: ' + str(currentLink['maskname']) + ' has no input mask'
            currentLink['op'] = 'PasteSplice'
            startNode = scModel.getGraph().get_node(edge[0]) #change to file
            endNode = scModel.getGraph().get_node(edge[1])
            imFile = select_region(os.path.join(projectDir, currentLink['inputmaskname']), os.path.join(projectDir, startNode['file']))
            dest = scModel.getGraph().add_node(imFile, seriesname=scModel.getSeriesName(), xpos=startNode['xpos'] + 50, ypos=startNode['ypos'] + 50,
                                          nodetype='base')
            newMod = maskgen.scenario_model.Modification('SelectRegion', None, software=Software('OpenCV', '2.4.11'))
            scModel.selectImage(edge[0])
            scModel.connect(destination=dest, mod=newMod)
            scModel.selectImage(dest)
            scModel.connect(endNode['seriesname'])

            print 'Replaced pasteduplicate with pastesplice in: ' + str(scModel.getName())
    #print 'Completed check_pasteduplicate'

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

def add_pastesplice_params(scModel,semantics):
    """
    Adds mandatory parameters to pastesplice operations in projects based on semantics.csv file
    :param scModel: opened JT project
    :return: None. Updates scModel
    """
    data = semantics
    defaults = {'donor cropped':'no', 'donor rotated':'no', 'purpose':'add', 'donor resized':'no'}

    name = scModel.getName()
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        if currentLink['op'] == 'PasteSplice':
            currentLink['recordMaskInComposite'] = 'true'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}


            # check for default args
            for arg in defaults.keys():
                if arg not in currentLink['arguments']:
                    currentLink['arguments'][arg] = defaults[arg]

            if 'subject' in currentLink['arguments']:
                continue
            # check semantics.csv data for subject of pastesplice
            try:
                id = data[name]
                #idx1 = id.index(edge[0])
                idx2 = id.index(edge[1])
                arg = id[idx2+1]
                currentLink['arguments']['subject'] = arg

            except (KeyError, ValueError):
                currentLink['arguments']['subject'] = 'other'
    #print 'Completed add_pastesplice_params'
# def inspect_mask_scope(scModel):
#     """
#     find masks that could represent local operations, and add 'local' arg if less than 50% of pixels changed
#     :param scModel: opened journaling project data
#     :param project: JSON project file
#     :return: None. Updates scModel.
#     """
#     localOps = ['FilterBlurMotion', 'AdditionalEffectFilterBlur', 'FilterBlurNoise', 'AdditionalEffectFilterSharpening',
#                 'ColorColorBalance']
#     projectDir = scModel.getGraph().dir
#     for edge in scModel.getGraph().get_edges():
#         currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
#         if currentLink['op'] in localOps:
#             imageFile = os.path.join(projectDir, currentLink['maskname'])
#             im = cv2.imread(imageFile, 0)
#             if 'arguments' not in currentLink.keys():
#                 currentLink['arguments'] = {}
#             if cv2.countNonZero(im) > im.size/2:
#                 currentLink['arguments']['local'] = 'yes'
#             else:
#                 currentLink['arguments']['local'] = 'no'

def replace_with_pastesampled(scModel):
    """
    Replace selected operations with PasteSampled, and update properties
    :param scModel: Opened project model
    :param project: Project JSON file
    :return: None. Updates JSON.
    """
    replace_list = ['PasteClone', 'FillRubberStamp', 'FillHealingBrush', 'FillCloneRubberStamp', 'FillRubberStampClone']
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        oldOp = currentLink['op']
        if oldOp in replace_list:
            currentLink['op'] = 'PasteSampled'
            currentLink['recordMaskInComposite'] = 'true'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            if oldOp == 'PasteClone' or oldOp == 'FillRubberStampClone':
                currentLink['arguments']['purpose'] = 'clone'
            elif oldOp == 'FillHealingBrush':
                currentLink['arguments']['purpose'] = 'heal'
            else:
                currentLink['arguments']['purpose'] = 'remove'
    #print 'Completed replace_with_pastesampled'


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
    #print 'Completed update_rotation'

def update_create_jpeg(scModel):
    """
    Update the create jpeg functionality
    :param scModel: Opened image project model
    :param project: Project JSON file
    :return: None. Update scModel
    """
    projectDir = scModel.getGraph().dir
    pairs = scModel.getTerminalToBasePairs()
    terminals = zip(*pairs)[0]
    nodesToRemove, originalHashes = loop_through_terminals(scModel, projectDir, terminals)

    if nodesToRemove:
        for node in nodesToRemove:
            scModel.selectImage(node)
            scModel.remove()

        CopyCompressionAndExifGroupOperation(scModel).performOp()

        newPairs = scModel.getTerminalToBasePairs()
        newTerminals = zip(*newPairs)[0]
        newHashes = loop_through_terminals(scModel, projectDir, newTerminals)[1]

        csvName = 'md5differences.csv'
        writeHeaders = not os.path.isfile(csvName)
        with open(csvName, 'a+') as csvFile:
            writer = csv.writer(csvFile)
            if writeHeaders:
                writer.writerow(['OriginalMD5', 'NewMD5', 'Project'])
            for idx, newHash in enumerate(newHashes):
                if newHash != originalHashes[idx]:
                    writer.writerow([originalHashes[idx], newHash, os.path.basename(scModel.getGraph().dir)])

        if nodesToRemove != []:
            print 'Updated JPEG group operation in project: ' + str(scModel.getName())


def loop_through_terminals(scModel, projectDir, terminals):
    """
    Loop through nodes to find create JPEG group operation
    :param scModel: Opened project model
    :param projectDir: Directory of project's images
    :param terminals: List of Terminal-Base pair tuples
    :return:
    """
    nodesToRemove = []
    hashes = []
    for t in terminals:
        pred = scModel.getGraph().predecessors(t)
        for p in pred:
            edge = scModel.getGraph().get_edge(p, t)
            if edge['op'] == 'AntiForensicCopyExif':
                pred2 = scModel.getGraph().predecessors(p)
                for p2 in pred2:
                    edge2 = scModel.getGraph().get_edge(p2, p)
                    if edge2['op'] == 'AntiForensicExifQuantizationTable':
                        nodesToRemove.extend([p, t])
                        hashes.append(hashlib.md5(open(os.path.join(projectDir, t+'.jpg'), 'rb').read()).hexdigest())

    return nodesToRemove, hashes

def update_username(scModel):
    """
    Update username from project
    :param scModel: Opened project
    :return:
    """
    usernames = {'smitha':'TheDoorKnob', 'shrivere':'FlowersOfWonderland', 'kozakj':'Walrus','ahill':'WhiteRabbit',
                 'andrewhill':'WhiteRabbit','cwhitecotton':'Jabberwocky', 'colewhitecotton':'Jabberwocky',
                 'catalingrigoras':'Hedgehogs', 'cgrigoras':'Hedgehogs', 'jzjalic':'Caterpillar', 'jameszjalic':'Caterpillar',
                 'kboschetto':'Dinah', 'karleeboschetto':'Dinah', 'jeffsmith':'DoorMouse', 'jsmith':'DoorMouse',
                 'mpippin':'MadHatter', 'meganpippin':'MadHatter', 'mlawson':'Seven', 'melissalawson':'Seven'}

    usr = get_username()
    if usr.lower() in usernames.keys():
        setPwdX(CustomPwdX(usernames[usr.lower()]))
        scModel.getGraph().replace_attribute_value('username', usr, usernames[usr.lower()])
    #print 'Completed update_username'

def add_fillcontentawarefill_args(scModel):
    """
    Add FillContentAwareFill operation argument 'purpose':'remove'. Also set 'recordMaskInComposite' to 'true'
    :param scModel:
    :return:
    """
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        if currentLink['op'] == 'FillContentAwareFill':
            currentLink['recordMaskInComposite'] = 'true'
            if 'arguments' not in currentLink:
                currentLink['arguments'] = {}
            if 'purpose' in currentLink['arguments']:
                continue
            currentLink['arguments']['purpose'] = 'remove'
    #print 'Completed add_fillcontentawarefill_args'

def fix_noncroplinks(scModel):
    """
    Remove 'location' from all links but crop
    :param scModel:
    :return:
    """
    for edge in scModel.getGraph().get_edges():
        currentLink = scModel.getGraph().get_edge(edge[0], edge[1])
        if currentLink['op'] != 'TransformCrop':
            if 'location' in currentLink:
                currentLink['location'] = '0,0'

def perform_update(project,args, error_writer, semantics):
    scModel = maskgen.scenario_model.ImageProjectModel(project)

    #inspect_mask_scope(scModel)
    update_rotation(scModel)
    label_project_nodes(scModel)
    if args.updateusername or args.all:
        update_username(scModel)
    if args.contentawarefillargs or args.all:
        add_fillcontentawarefill_args(scModel)
    if args.updatephotoshop or args.all:
        update_photoshop_version(scModel)
    if args.replacewithpastesampled or args.all:
        replace_with_pastesampled(scModel)
    if args.replacepasteduplicate or args.all:
        check_pasteduplicate(scModel)
    if args.pastespliceargs or args.all:
        add_pastesplice_params(scModel,semantics)
    if args.replacejpeg or args.all:
        update_create_jpeg(scModel)
    if args.renamedonors or args.all:
        rename_donorsandbase(scModel,args.updatedir)
    if args.composites or args.all:
        scModel.constructComposites()
        scModel.constructDonors()
        processProjectProperties(scModel)
    if args.redomasks or args.all:
        rebuild_masks(scModel)
    if args.all:
        fix_noncroplinks(scModel)

    scModel.save()
    scModel.export(args.updatedir)
    if args.extractjson:
        dest = os.path.join(args.updatedir, os.path.split(project)[1])
        shutil.copy(project,dest)
    error_list = scModel.validate()
    for err in error_list:
        error_writer.writerow((scModel.getName(), str(err)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=True, help='Directory of projects')
    parser.add_argument('-s', '--skipdir', required=True, help='Directory of skipped projects')
    parser.add_argument('-u', '--updatedir', required=True, help='Directory of updated projects')
    parser.add_argument('-c', '--composites', help='Reconstruct composite images',action='store_true')
    parser.add_argument('-rd', '--renamedonors', help='Rename donor images',action='store_true')
    parser.add_argument('-ej', '--extractjson', help='Extract JSON files', action='store_true')
    parser.add_argument('-rc', '--redomasks', help='Rebuild link masks',action='store_true')
    parser.add_argument('-rp', '--replacepasteduplicate', help='Replace PasteDuplicate with PasteSplice, using input masks.', action='store_true')
    parser.add_argument('-rj', '--replacejpeg', help='Update create jpeg group operation', action='store_true')
    parser.add_argument('-up', '--updatephotoshop', help='Replace Photoshop version CC16.16 with CC15.5.0', action='store_true')
    parser.add_argument('-rs', '--replacewithpastesampled', help='Replace PasteClone, FillRubberStamp, FillHealingBrush, and FillRubberStampClone with PasteSampled', action='store_true')
    parser.add_argument('-uu', '--updateusername', help='Update username based on current', action='store_true')
    parser.add_argument('-cf', '--contentawarefillargs', help='Add \'purpose\' arguments for content aware fill', action='store_true')
    parser.add_argument('-ps', '--pastespliceargs', help='Add default arguments to pastesplice operation {donor cropped:no, donor rotated:no, purpose:add, donor resized:no}. '
                                                         'Subject will be added based on semantics.csv, or be set to \'other\' if the operation is not found in file')

    parser.add_argument('-a', '--all', help='Perform all updates', action='store_true')
    args = parser.parse_args()

    data = {}
    if os.path.exists('semantics.csv'):
        with open('semantics.csv') as csvFile:
            rdr = csv.reader(csvFile)
            for row in rdr:
                try:
                    data[row[0]].extend(row[1:4])
                except KeyError:
                    data[row[0]] = row[1:4]

    ops = loadOperations("operations.json")
    soft = loadSoftware("software.csv")
    loadProjectProperties("project_properties.json")

    with open(os.path.join(args.updatedir,'ErrorReport_' + str(os.getpid()) + '.csv'), 'w') as csvfile:
        error_writer = csv.writer(csvfile, delimiter = ' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        zippedProjects = bulk_export.pick_zipped_projects(args.dir)
        total = len(zippedProjects)
        count = 1
        for zippedProject in zippedProjects:
            loadPlugins()
            dir = tempfile.mkdtemp()
            try:
                if extract_archive(zippedProject, dir):
                    for project in bulk_export.pick_projects(dir):
                        print 'Project updating: ' + zippedProject
                        perform_update(project, args, error_writer, data)
                        print 'Project updated [' + str(count) + '/' + str(total) + '] ' + zippedProject
                        os.remove(os.path.join(args.dir,zippedProject))
                else:
                    print 'Project skipped ' + zippedProject
                    shutil.move(zippedProject, args.skipdir)
            except Exception as e:
                        print e
                        print 'Project skipped: ' + zippedProject
                        shutil.move(zippedProject,args.skipdir)

            count += 1
            shutil.rmtree(dir)

if __name__ == '__main__':
    main()
