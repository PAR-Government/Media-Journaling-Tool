# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import logging
from maskgen.software_loader import getFileName

# tools for assisting with S3 and HTTP functionality

def loadS3(values):
  import boto3
  import os
  logging.getLogger('maskgen').info( 'Download operations and software via S3')
  s3 = boto3.client('s3','us-east-1')
  BUCKET = values[0][0:values[0].find('/')]
  DIR=values[0][values[0].find('/')+1:]
  place = getFileName('operations.json')
  if place is None:
      place = os.path.abspath(os.getenv('MASKGEN_RESOURCES', '.'))
  else:
      place = os.path.dirname(place)
  s3.download_file(BUCKET, DIR + "/operations.json", os.path.join(place,"operations.json"))
  s3.download_file(BUCKET, DIR + "/software.csv", os.path.join(place,"software.csv"))
  s3.download_file(BUCKET, DIR + "/project_properties.json", os.path.join(place,"project_properties.json"))
  s3.download_file(BUCKET, DIR + "/ManipulatorCodeNames.txt", os.path.join(place, "ManipulatorCodeNames.txt"))

def loadHTTP(values):
    import requests
    import os
    logging.getLogger('maskgen').info( 'Download operations and software via HTTP')
    head = {}
    place = getFileName('operations.json')
    if place is None:
        place = os.path.abspath(os.getenv('MASKGEN_RESOURCES', '.'))
    else:
        place = os.path.dirname(place)
    for p in range(1, len(values)):
        name = values[p].split(':')[0].strip()
        val = values[p].split(':')[1].strip()
        head[name]=val
    r = requests.get(values[0] + '/operations.json',headers=head)
    if r.status_code < 300:
      with open(os.path.join(place,"operations.json"), 'w') as f:
          f.write(r.content)
    r = requests.get(values[0] + '/software.csv',headers=head)
    if r.status_code < 300:
      with open(os.path.join(place,"software.csv"), 'w') as f:
          f.write(r.content)


