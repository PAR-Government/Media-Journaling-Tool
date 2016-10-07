import argparse
import os
import maskgen.scenario_model
import bulk_export
import tempfile
from maskgen.image_graph import extract_archive
from maskgen.graph_rules import processProjectProperties
import hashlib
import shutil

def label_project_nodes(scModel):
    """
    Labels all nodes on a project
    :param scModel: scenario model
    """
    p = scModel.getNodeNames()
    for node in p:
        scModel.labelNodes(node)

def rebuild_masks(scModel):
    """
    Rebuild all edge masks
    :param scModel: scenario model
    :return:
    """
    for edge in scModel.getGraph().get_edges():
        scModel.select(edge)
        scModel.reproduceMask()

def rename_donors(scModel,updatedir):
    """
    Rename donor images with MD5
    :param scModel: scenario model
    :return:
    """
    for node in scModel.getNodeNames():
        nodeData = scModel.getGraph().get_node(node)
        if nodeData['nodetype'] == 'donor':
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

def perform_update(project,args):
    scModel = maskgen.scenario_model.ImageProjectModel(project)
    label_project_nodes(scModel)
    if args.renamedonors:
        rename_donors(scModel,args.updatedir)
    if args.composites:
        scModel.constructComposites()
        scModel.constructDonors()
        processProjectProperties(scModel)
    if args.redomasks:
        rebuild_masks(scModel)
    scModel.save()
    scModel.export(args.updatedir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=True, help='Directory of projects')
    parser.add_argument('-u', '--updatedir', required=True, help='Directory of updated projects')
    parser.add_argument('-c', '--composites', required=False, help='Reconstruct composite images',action='store_true')
    parser.add_argument('-rd', '--renamedonors', required=False, help='Rename donor images',action='store_true')
    parser.add_argument('-rc', '--redomasks', required=False, help='Rebuild link masks',action='store_true')
    args = parser.parse_args()

    zippedProjects = bulk_export.pick_zipped_projects(args.dir)
    total = len(zippedProjects)
    count = 1
    for zippedProject in zippedProjects:
        dir = tempfile.mkdtemp()
        if extract_archive(zippedProject, dir):
            for project in bulk_export.pick_projects(dir):
                perform_update(project, args)
                print 'Project updated [' + str(count) + '/' + str(total) + '] ' + zippedProject
                count += 1
        else:
            print 'Project skipped ' + zippedProject

if __name__ == '__main__':
    main()
