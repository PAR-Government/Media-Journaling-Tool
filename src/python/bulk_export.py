import os
import sys
import argparse
import shutil
import boto3

def pick_dirs(directory):
    """
    Finds all subdirectories in directory containing a .json file
    :param directory: string containing directory of subdirectories to search
    :return: list containing valid project directories
    """
    ext = '.json'
    subs = [x[0] for x in os.walk(directory)]
    projects = []

    for sub in subs:
        for File in os.listdir(sub):
            if File.endswith(ext):
                projects.append(sub)
                break
    return projects

def upload_projects(values, projects):
    """
    Zips project directories and uploads them to S3
    :param values: bucket/dir S3 location
    :param projects: list of project directories
    """
    s3 = boto3.client('s3', 'us-east-1')

    # handles file paths that use / or \
    bucketDir = values.replace('\\','/').split('/')

    for project in projects:
        zip = shutil.make_archive(project.replace('\\','/').split('/')[-1],
                                  'zip', project)
        s3.upload_file(bucketDir[0], bucketDir[1], zip)
        os.remove(zip)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir',  help='directory of projects')
    parser.add_argument('-s', '--s3',   help='bucket/path of s3 storage')
    args = parser.parse_args()

    dirs = pick_dirs(args.dir)
    if not dirs:
        sys.exit('No projects found!')

    upload_projects(args.s3, dirs)

if __name__ == '__main__':
    main()