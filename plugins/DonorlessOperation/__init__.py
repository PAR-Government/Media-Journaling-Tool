import logging
from maskgen import video_tools
import random
import maskgen.video_tools
import os
import maskgen
import json

plugin = "DonorPicker"
def transform(img, source, target, **kwargs):
    valid = []
    possible = []
    data = {}
    logging.getLogger('maskgen').info(str(kwargs))
    for f in os.listdir(kwargs['Directory']):
        if os.path.splitext(f)[1] == '.json':
            data = json.load(open(os.path.join(kwargs['Directory'],f)))
        elif video_tools.get_shape_of_video(os.path.join(kwargs['Directory'], f)) == video_tools.get_shape_of_video(source):
            possible.append(os.path.join(kwargs['Directory'],f))

    for d in possible:
        if os.path.split(d)[1] in data:
            valid.append(d)
    if len(valid) == 0:
        raise ValueError('No donors of correct size available')
    donor = valid[0]

    if kwargs['Pick Preference'] == 'Random':
        donor = valid[random.randint(0,len(valid)-1)]
    elif kwargs['Pick Preference'] == 'By Name':
        for v in valid:
            if os.path.splitext(source)[0] in (os.path.split(v)[1]):
                donor = v
    elif kwargs['Pick Preference'] =='Specific':
        donor = kwargs['Donator']
    data = data[os.path.split(donor)[1]]
    data['Donator'] = donor
    logging.getLogger('maskgen').info("Donor Selected: {}".format(donor))
    #shutil.copy((os.path.join(kwargs['Directory'],f)),os.path.join(scenario_model.get, f))
    #result, err = callPlugin(kwargs['Plugin'],img,source,target,**kwargs)
    #final = {k: v for d in [result, data] for k, v in d.items()} if result is not None else data
    logging.getLogger('maskgen').info(str(data))
    #os.remove(os.path.join(".", f))
    return data,None

def operation():
    return {'name': 'SelectRegion',
            'category': 'Select',
            'type': 'Selector',
            'description': 'Pick a donor and other data from a directory',
            'software': 'Maskgen',
            'version': maskgen.__version__,
            'arguments': {
                'Directory': {
                    'type': 'file',
                    'defaultvalue': '.',
                    'description': 'Directory full of possible PRNU choices'
                },
                'Pick Preference': {
                    'type': 'list',
                    'values': ['Random', 'By Name', 'Specific'],
                    'defaultvalue': 'Random',
                    'description': 'Select the deciding factor for which video will be selected from the directory'
                }
            },
            'transitions': [
                'video.video'
                'image.image'
            ]
            }