import argparse
from maskgen.tool_set import *

def exporttos3(path):
    import boto3
    s3 = boto3.client('s3', 'us-east-1')
    BUCKET = 'medifor'
    DIR = 'par/journal/projects'
    print 'Upload to s3://' + BUCKET + '/' + DIR + '/' + os.path.split(path)[1]
    s3.upload_file(path, BUCKET, DIR + '/' + os.path.split(path)[1])
    os.remove(path)

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=True, help='Directory of projects')
    parser.add_argument('-s', '--skipfile', required=False, help='Projects to Skip')
    args = parser.parse_args()

    skips = []
    if os.path.exist(args.skipfile is not None):
        with open(args.skipfile, 'r') as skip:
            skips = skip.readlines()
        skips = [x.strip() for x in skips]

    pid = os.getpid()
    with open('done_' + str(pid) +'.txt', 'w') as done:
        zippedProjects = pick_zipped_projects(args.dir)
        for zippedProject in zippedProjects:
            if zippedProject not in skips:
                 exporttos3(zippedProject)
                 done.write(zippedProject + '\n')

if __name__ == '__main__':
    main()
