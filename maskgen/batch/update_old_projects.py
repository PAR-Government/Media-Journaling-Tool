import argparse
import os
import json
import cv2
import maskgen.scenario_model
import bulk_export

replacements = {'FillCloneRubberStamp':'PasteClone'}
localOps = ['FilterBlurMotion', 'AdditionalEffectFilterBlur', 'FilterBlurNoise', 'AdditionalEffectFilterSharpening',
            'ColorColorBalance']

def label_project_nodes(project):
    """
    Labels all nodes on a project
    :param project: path to a project json file
    :return: None. Updates JSON.
    """
    sm = maskgen.scenario_model.ImageProjectModel(project)
    p = sm.getNodeNames()
    for node in p:
        sm.labelNodes(node)
    sm.save()


def replace_op_names(data):
    """
    Replaces select operation names
    :param data: json file
    :return: None. Updates json.
    """
    global replacements
    numLinks = len(data['links'])
    for link in xrange(numLinks):
        currentLink = data['links'][link]
        if currentLink['op'] in replacements.keys():
            currentLink['op'] = replacements[currentLink['op']]


def inspect_masks(d, data):
    """
    find masks that could represent local operations, and add 'local' arg if less than 50% of pixels changed
    :param d: project directory
    :param data: json data
    :return: None. Updates json.
    """
    global localOps
    numLinks = len(data['links'])
    for link in xrange(numLinks):
        currentLink = data['links'][link]
        if currentLink['op'] in localOps:
            imageFile = os.path.join(os.path.dirname(d), currentLink['maskname'])
            im = cv2.imread(imageFile, 0)
            if 'arguments' not in currentLink.keys():
                currentLink['arguments'] = {}
            if cv2.countNonZero(im) > im.size/2:
                currentLink['arguments']['local'] = 'yes'
            else:
                currentLink['arguments']['local'] = 'no'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=True, help='Directory of projects')
    args = parser.parse_args()

    dirs = bulk_export.pick_projects(args.dir)
    total = len(dirs)
    count = 1
    for d in dirs:
        label_project_nodes(d)
        with open(d, 'r+') as f:
            data = json.load(f)
            replace_op_names(data)
            inspect_masks(d, data)
            f.seek(0)
            json.dump(data, f, indent=2)
        print 'Project updated [' + str(count) + '/' + str(total) + '] '+ os.path.basename(d)
        count+=1

if __name__ == '__main__':
    main()
