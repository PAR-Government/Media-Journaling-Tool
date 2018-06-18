import os
import glob
import maskgen

def transform(img, source, target, **kwargs):
	dir = kwargs['directory']
	masks = glob.glob(os.path.join(dir, os.path.splitext(source)[0]) + '*')[0]
	analysis = {'override_target': masks}

	return analysis, None


def operation():
	return {
		'category': 'Select',
		'name': 'SelectRegion',
		'description': 'Mask Selector: ',
		'software': 'Maskgen',
		'version': maskgen.__version__,
		'arguments': {'directory': {'type': "text", 'description': 'Directory of Masks'}},
		'transitions': [
			'image.image'
		]
	}


def suffix():
	return '.png'
