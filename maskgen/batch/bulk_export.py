import os
import sys
import argparse
import maskgen.scenario_model
from maskgen.graph_rules import processProjectProperties
import csv
from maskgen.batch import pick_projects

def upload_projects(s3dir, dir, error_writer):
    """
    Uploads project directories to S3 bucket
    :param values: bucket/dir S3 location
    :param dir: directory of project directories
    """

    projects = pick_projects(dir)
    if not projects:
        sys.exit('No projects found!')

    for project in projects:
        scModel = maskgen.scenario_model.loadProject(project)
        processProjectProperties(scModel)
        error_list = scModel.exporttos3(s3dir)
        if len(error_list) > 0:
            for err in error_list:
                print err
            raise ValueError('Export Failed')
        for err in scModel.validate():
            error_writer.writerow((scModel.getName(), str(err)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--projects',  help='directory of projects')
    parser.add_argument('-s', '--s3',   help='bucket/path of s3 storage')
    args = parser.parse_args()

    with open(os.path.join('ErrorReport_' + str(os.getpid()) + '.csv'), 'w') as csvfile:
        error_writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        upload_projects(args.s3, args.projects,error_writer)

if __name__ == '__main__':
    main()
