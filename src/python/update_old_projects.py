import argparse
import os
import json
import cv2
from PIL import Image
import scenario_model
import bulk_export

replacements = {'FillCloneRubberStamp':'PasteClone'}
localOps = ['FilterBlurMotion', 'AdditionalEffectFilterBlur', 'FilterBlurNoise', 'AdditionalEffectFilterSharpening',
            'ColorColorBalance']

def label_project_nodes(project):
    sm = scenario_model.ImageProjectModel(project)
    p = sm.getNodeNames()
    for node in p:
        sm.labelNodes(node)
    sm.save()

def replace_op_names(d):
    global replacements
    lines = []
    with open(d) as json:
        for line in json:
            for k,v in replacements.iteritems():
                line = line.replace(k, replacements[k])
            lines.append(line)

    with open(d, 'w') as newjson:
        for line in lines:
            newjson.write(line)

def inspect_masks(d):
    global localOps
    with open(d, 'r+') as f:
        data = json.load(f)
        numLinks = len(data['links'])
        for link in xrange(numLinks):
            currentLink = data['links'][link]
            if currentLink['op'] in localOps:
                imageFile = os.path.join(os.path.dirname(d), currentLink['maskname'])
                im = cv2.imread(imageFile, 0)
                if cv2.countNonZero(im) > im.size/2:
                    currentLink['arguments']['local'] = 'yes'
                else:
                    currentLink['arguments']['local'] = 'no'
        f.seek(0)
        json.dump(data, f, indent=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=True, help='Directory of projects')
    args = parser.parse_args()

    dirs = bulk_export.pick_dirs(args.dir)
    total = len(dirs)
    count = 1
    for d in dirs:
        label_project_nodes(d)
        replace_op_names(d)
        inspect_masks(d)
        print 'Project updated [' + str(count) + '/' + str(total) + '] '+ os.path.basename(d)
        count+=1

if __name__ == '__main__':
    main()
