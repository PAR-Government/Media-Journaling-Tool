import argparse
import os
from maskgen.tool_set import *
import maskgen
from maskgen.image_graph import extract_archive
import shutil
import tarfile

def fetchfromS3(dir, file):
    import boto3
    #s3 = boto3.client('s3', 'us-east-1')
    BUCKET = 'medifor'
    DIR = 'par/journal/'
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(BUCKET)
    my_bucket.download_file(DIR + file, os.path.join(dir, file))

def pick_projects(directory):
    """
    Finds all subdirectories in directory containing a .json file
    :param directory: string containing directory of subdirectories to search
    :return: list projects found under the given directory
    """
    ext = '.json'
    subs = [x[0] for x in os.walk(directory)]
    projects = []

    for sub in subs:
        files = []
        for f in os.listdir(sub):
            if f.endswith(ext):
                files.append(f)
        if len(files) > 0:
            sizes = [os.stat(os.path.join(sub, pick)).st_size for pick in files]
            max_size = max(sizes)
            index = sizes.index(max_size)
            projects.append(os.path.join(sub, files[index]))
    return projects

def extract_frommarchive(fname, dir):
    try:
        archive = tarfile.open(fname, "r:gz", errorlevel=2)
    except Exception as e:
        try:
            archive = tarfile.open(fname, "r", errorlevel=2)
        except Exception as e:
            print e
            return False

    if not os.path.exists(dir):
        os.mkdir(dir)
    for n in archive.getnames():
        if n.endswith(".json"):
            archive.extract(n,path=dir)
    #archive.extractall(dir)
    archive.close()

    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=True, help='Directory of projects')
    parser.add_argument('-cf', '--checkfilelist', required=True, help='Directory of projects')
    parser.add_argument('-mf', '--masterfilelist', required=True, help='Directory of projects')
    args = parser.parse_args()

    list_of_files = []
    with open(args.checkfilelist) as fp:
        list_of_files = fp.readlines()
        list_of_files = [x.strip() for x in list_of_files]
    list_of_master_files = []

    with open(args.masterfilelist) as fp:
        list_of_master_files = fp.readlines()
        #list_of_master_files = [x.strip() for x in list_of_master_files]
        list_of_master_files = [x[0:x.rfind('.')] for x in list_of_master_files]

    for afile in list_of_files:
        if not os.path.exists(os.path.join(args.dir,afile)):
           fetchfromS3(args.dir,afile)
        print afile
        file = os.path.join(args.dir,afile)
        extract_frommarchive(file, args.dir)
        for project in pick_projects(args.dir):
            scModel = maskgen.scenario_model.ImageProjectModel(project)
            if scModel.getName() in list_of_master_files:
                os.remove(file)
            shutil.rmtree(os.path.split(project)[0])

if __name__ == '__main__':
    main()
