# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

import maskgen

def transform(img,source,target,**kwargs):
  return None,None

# the actual link name to be used.
# the category to be shown
def operation():
  return {'name':'Blur',
          'category':'Filter',
          'description':'Gaussian Blur',
          'software':'maskgen',
          'version':maskgen.__version__,
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return None