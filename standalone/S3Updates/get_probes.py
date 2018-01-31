import argparse
import os
from maskgen.tool_set import *
from maskgen.image_graph import extract_archive
from maskgen.batch import BatchProcessor, pick_projects
import csv
from functools import partial
import tempfile
import shutil
from maskgen.services.probes import archive_probes

"""
Given a set of projects, produce archives containing probe images and CSV file describing probes
"""
prefLoader = MaskGenLoader()

def fetchfromS3(dir, location, file):
    import boto3
    BUCKET = location.split('/')[0].strip()
    DIR = location[location.find('/') + 1:].strip() +'/'
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(BUCKET)
    my_bucket.download_file(DIR + file, os.path.join(dir, file))

def processProject(directory, file_to_process):
    import thread
    """
    :param args:
    :param functions:
    :param file_to_process:
    :return:
    @type file_to_process : str
    """
    dir = os.path.join(tempfile.gettempdir(),'probe_{}_{}'.format(os.getpid(),thread.get_ident()))
    os.mkdir(dir)
    try:
        fetchfromS3(dir, 'medifor/par/journal/ingested',file_to_process)
        extract_archive(os.path.join(dir, file_to_process), dir)
        for project in pick_projects(dir):
            archive_probes(project, directory=directory)
    finally:
        shutil.rmtree(dir)
    return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f',  '--file', required=True, help='File of projects')
    parser.add_argument('-t',  '--threads', required=False, default=1, help='Threads to Use')
    parser.add_argument('-cf', '--completefile', required=True, help='Projects to Completed')
    parser.add_argument('-d',  '--directory', required=True, help='Place to put the results',default='.')
    args = parser.parse_args()


    with open(args.file, 'r') as input_file:
        csvreader = csv.reader(input_file, delimiter=',')
        files_to_process = [row[0] for row in csvreader]


    processor = BatchProcessor(args.completefile,files_to_process,threads=int(args.threads))
    func = partial(processProject, args.directory)
    processor.process(func)

if __name__ == '__main__':
    main()
