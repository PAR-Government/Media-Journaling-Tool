from __future__ import print_function
import os
import sys
import argparse
import maskgen.scenario_model
from maskgen.graph_rules import processProjectProperties
import csv
from maskgen.batch import pick_projects
from maskgen.tool_set import CustomPwdX, setPwdX, get_username


def upload_projects(s3dir, dir, qa, username, error_writer):
    """
    Uploads project directories to S3 bucket
    :param s3dir: bucket/dir S3 location
    :param dir: directory of project directories
    :param qa: bool for if the projects need to be qa'd
    :param username: export and qa username
    """

    projects = pick_projects(dir)
    if not projects:
        sys.exit('No projects found!')

    for project in projects:
        scModel = maskgen.scenario_model.loadProject(project)
        if username is None:
            setPwdX(CustomPwdX(scModel.getGraph().getDataItem("username")))
        else:
            setPwdX(CustomPwdX(username))

        processProjectProperties(scModel)
        #scModel.renameFileImages()
        if qa:
            scModel.set_validation_properties("yes", get_username(), "QA redone via Batch Updater")
        error_list = scModel.exporttos3(s3dir)
        if len(error_list) > 0:
            for err in error_list:
                print (err)
            raise ValueError('Export Failed')
        for err in scModel.validate():
            error_writer.writerow((scModel.getName(), str(err)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--projects',  help='directory of projects')
    parser.add_argument('-s', '--s3',   help='bucket/path of s3 storage')
    parser.add_argument('--qa', help="option argument to QA the journal prior to uploading", required=False, action="store_true")
    parser.add_argument('-u', '--username', help="optional username", required=False)
    args = parser.parse_args()

    with open(os.path.join('ErrorReport_' + str(os.getpid()) + '.csv'), 'w') as csvfile:
        error_writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        upload_projects(args.s3, args.projects, args.qa, args.username, error_writer)

if __name__ == '__main__':
    main()
