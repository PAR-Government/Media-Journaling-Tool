# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from __future__ import print_function
import os
import sys
import argparse
import maskgen.scenario_model
from maskgen.graph_rules import processProjectProperties
from  maskgen import maskGenPreferences
import csv
from maskgen.batch import pick_projects
from maskgen.userinfo import get_username, setPwdX,CustomPwdX
from maskgen.validation.core import Severity, ValidationMessage, hasErrorMessages
from maskgen.preferences_initializer import initialize
from maskgen import maskGenPreferences
import logging

def upload_projects(s3dir, dir, qa, username, organization, error_writer, updatename, ignore_errors, redactions):
    """
    Uploads project directories to S3 bucket
    :param s3dir: bucket/dir S3 location
    :param dir: directory of project directories
    :param qa: bool for if the projects need to be qa'd
    :param username: export and qa username
    :param updatename: change the project username to match username value
    :param organization: change project organization
    """

    projects = pick_projects(dir)
    if not projects:
        sys.exit('No projects found!')
    for project in projects:
        scModel = maskgen.scenario_model.loadProject(project)
        if username is None:
            setPwdX(CustomPwdX(scModel.getGraph().getDataItem("username")))
        else:
            if (updatename == True):
                oldValue = scModel.getProjectData('username')
                scModel.setProjectData('creator', username)
                scModel.setProjectData('username', username)
                scModel.getGraph().replace_attribute_value('username', oldValue, username)
        if organization is not None:
            scModel.setProjectData('organization', organization)
            scModel.save()
        processProjectProperties(scModel)
        if qa:
            username = username if username is not None else get_username()
            scModel.set_validation_properties("yes", username, "QA redone via Batch Updater")
        errors = scModel.validate(external=True)
        for err in errors:
            error_writer.writerow((scModel.getName(), err.Severity.name,err.Start,err.End,err.Message))
        if not ignore_errors and hasErrorMessages(errors,  contentCheck=lambda x: len([m for m in redactions if m not in x]) == 0 ):
	    logging.getLogger('maskgen').error('Validaiton Errors for {}'.format(scModel.getName()))
            continue
        if s3dir is None:
            error_list = scModel.export('.')
        else:
            error_list = scModel.exporttos3(s3dir, redacted=redactions)
        if len(error_list) > 0:
            for err in error_list:
                print (err)
            raise ValueError('Export Failed')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--projects',  help='directory of projects')
    parser.add_argument('-s', '--s3',   help='bucket/path of s3 storage', required=False)
    parser.add_argument('--qa', help="option argument to QA the journal prior to uploading", required=False, action="store_true")
    parser.add_argument('-u', '--username', help="optional username", required=False)
    parser.add_argument('-o', '--organization', help="update organization in project", required=False)
    parser.add_argument('-n', '--updatename', help="should update username in project", required=False, action="store_true")
    parser.add_argument('-r','--redacted',help='comma separated list of file argument to exclude from export',default='', required=False)
    parser.add_argument('-i','--ignore',help='ignore errors',default='', required=False)
    args = parser.parse_args()

    initialize(maskGenPreferences, username=args.username)
    with open(os.path.join('ErrorReport_' + str(os.getpid()) + '.csv'), 'w') as csvfile:
        error_writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        upload_projects(args.s3, args.projects, args.qa, args.username, args.organization, error_writer,
                        args.updatename,
 			args.ignore,
                        [redaction.strip() for redaction in args.redacted.split(',')])

if __name__ == '__main__':
    main()
