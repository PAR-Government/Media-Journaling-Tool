import os
import sys
import argparse
import maskgen.scenario_model

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

def pick_zipped_projects(directory):
    """
    Finds all subdirectories in directory containing a .json file
    :param directory: string containing directory of subdirectories to search
    :return: list projects found under the given directory
    """
    ext = '.tgz'
    subs = [x[0] for x in os.walk(directory)]
    projects = []

    for sub in subs:
        for f in os.listdir(sub):
            if f.endswith(ext):
                projects.append(os.path.join(sub,f))
    return projects


def upload_projects(values, dir):
    """
    Uploads project directories to S3 bucket
    :param values: bucket/dir S3 location
    :param dir: directory of project directories
    """

    projects = pick_projects(dir)
    if not projects:
        sys.exit('No projects found!')

    for project in projects:
        sm = maskgen.scenario_model.loadProject(project)
        sm.exporttos3(values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir',  help='directory of projects')
    parser.add_argument('-s', '--s3',   help='bucket/path of s3 storage')
    args = parser.parse_args()

    upload_projects(args.s3, args.dir)

if __name__ == '__main__':
    main()
