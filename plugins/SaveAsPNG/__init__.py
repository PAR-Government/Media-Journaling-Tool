from PIL import Image

def transform(img,source,target, **kwargs):

    im = Image.open(source)
    im.save(target)
    
    return False,None
    
def operation():
    return ['OutputPng','Output', 
            'Save an image as .PNG', 'PIL', '1.1.7']
    
def args():
    return None

def suffix():
    return '.png'
