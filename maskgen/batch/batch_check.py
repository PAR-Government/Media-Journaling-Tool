import argparse
import os
import json
import cv2
import numpy as np
from PIL import Image
import maskgen.scenario_model
from maskgen.tool_set import *
from maskgen.batch import bulk_export
import tempfile
from maskgen.image_graph import extract_archive
from maskgen.graph_rules import processProjectProperties
from maskgen.group_operations import CopyCompressionAndExifGroupOperation
from maskgen.software_loader import Software,loadOperations,loadProjectProperties,loadSoftware
from maskgen.plugins import loadPlugins
import hashlib
import shutil
import sys
import csv
#from memory_profiler import profile

#@profile
def perform_update(project,args, skipReport, skips):
    scModel = maskgen.scenario_model.ImageProjectModel(project)
    print 'User: ' + scModel.getGraph().getDataItem('username')
    scModel.getProbeSet()
    scModel.toCSV(os.path.join(scModel.get_dir(),'colors.csv'))
    scModel.export(args.tempfolder,include=['colors.csv'])
    if scModel.getName() in skips:
        skipReport.write(scModel.getName() + '.tgz')

def fetchfromS3(dir, location, file):
    import boto3
    BUCKET = location.split('/')[0].strip()
    DIR = location[location.find('/') + 1:].strip() +'/'
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(BUCKET)
    my_bucket.download_file(DIR + file, os.path.join(dir, file))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f',  '--file', required=True, help='File of projects')
    parser.add_argument('-df', '--downloadfolder', required=True, help='Download folder')
    parser.add_argument('-cf', '--completefile', required=True, help='Projects to Completed')
    parser.add_argument('-tf', '--tempfolder', required=True, help='Projects to Completed')
    args = parser.parse_args()

    skips = []
    if os.path.exists(args.completefile):
        with open(args.completefile, 'r') as skip:
            skips = skip.readlines()
        skips = [x.strip() for x in skips]

    files_to_process = []
    with open(args.file, 'r') as input_file:
        files_to_process = input_file.readlines()
    files_to_process = [x.strip() for x in files_to_process]

    ops = loadOperations("operations.json")
    soft = loadSoftware("software.csv")
    loadProjectProperties("project_properties.json")
    loadPlugins()

    count = 1
    total = len(files_to_process)

    with open(args.completefile, 'a') as done_file:
        with open(os.path.join('ErrorReport_' + str(os.getpid()) + '.csv'), 'w') as csvfile:
            error_writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for file_to_process in files_to_process:
                if file_to_process in skips:
                    count += 1
                    continue
                dir = tempfile.mkdtemp(dir=args.tempfolder)
                try:
                    fetchfromS3(dir,args.downloadfolder,file_to_process)
                    extract_archive(os.path.join(dir,file_to_process), dir)
                    # remove to be replaced
                    os.remove(os.path.join(dir,file_to_process))
                    for project in bulk_export.pick_projects(dir):
                        print 'Project updating: ' + file_to_process
                        perform_update(project, args, error_writer, skips)
                        print 'Project updated [' + str(count) + '/' + str(total) + '] ' + file_to_process
                        done_file.write(file_to_process + '\n')
                        done_file.flush()
                        csvfile.flush()
                except Exception as e:
                    print e
                    print 'Project skipped: ' + file_to_process
                sys.stdout.flush()
                count += 1
                shutil.rmtree(dir)

if __name__ == '__main__':
    main()
