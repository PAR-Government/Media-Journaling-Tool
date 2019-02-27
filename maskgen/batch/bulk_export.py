# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from __future__ import print_function

import sys
import argparse
import maskgen.scenario_model
from maskgen.graph_rules import processProjectProperties
from maskgen.batch import pick_projects, BatchProcessor
from maskgen.userinfo import get_username, setPwdX,CustomPwdX
from maskgen.validation.core import  hasErrorMessages
from maskgen.preferences_initializer import initialize
from maskgen.external.exporter import ExportManager
import logging

export_manager = ExportManager()


def upload_projects(args, project):
    """
    Uploads project directories to S3 bucket
    :param s3dir: bucket/dir S3 location
    :param dir: directory of project directories
    :param qa: bool for if the projects need to be qa'd
    :param username: export and qa username
    :param updatename: change the project username to match username value
    :param organization: change project organization
    """
    s3dir = args.s3
    qa = args.qa
    username = args.username
    organization = args.organization
    updatename = args.updatename
    ignore_errors = args.ignore
    log = logging.getLogger('maskgen')
    redactions= [redaction.strip() for redaction in args.redacted.split(',')]
    scModel = maskgen.scenario_model.loadProject(project)
    if username is None:
        setPwdX(CustomPwdX(scModel.getGraph().getDataItem("username")))
    else:
        if updatename:
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
    errors = [] if args.skipValidation else scModel.validate(external=True)
    if ignore_errors or not hasErrorMessages(errors,  contentCheck=lambda x: len([m for m in redactions if m not in x]) == 0 ):
        path, error_list = scModel.export('.', redacted=redactions)
        if path is not None and (ignore_errors or len(error_list) == 0):
            export_manager.sync_upload(path, s3dir)
        if len(error_list) > 0:
            for err in error_list:
                log.error(str(err))
            raise ValueError('Export Failed')
    return errors

def main(argv=sys.argv[1:]):
    from functools import partial
    parser = argparse.ArgumentParser()
    parser.add_argument('--threads', default=1, required=False, help='number of projects to build')
    parser.add_argument('-d', '--projects', help='directory of projects')
    parser.add_argument('-s', '--s3', help='bucket/path of s3 storage', required=False)
    parser.add_argument('--qa', help="option argument to QA the journal prior to uploading", required=False,
                        action="store_true")
    parser.add_argument('-u', '--username', help="optional username", required=False)
    parser.add_argument('-o', '--organization', help="update organization in project", required=False)
    parser.add_argument('-n', '--updatename', help="should update username in project", required=False,
                        action="store_true")
    parser.add_argument('-r', '--redacted', help='comma separated list of file argument to exclude from export',
                        default='', required=False)
    parser.add_argument('-v', '--skipValidation', help='skip validation',action="store_true")
    parser.add_argument('-i', '--ignore', help='ignore errors', default='', required=False)
    parser.add_argument('--completeFile', default=None, help='A file recording completed projects')
    args = parser.parse_args(argv)

    iterator = pick_projects(args.projects)
    processor = BatchProcessor(args.completeFile, iterator, threads=args.threads)
    func = partial(upload_projects, args)
    return processor.process(func)


if __name__ == '__main__':
    main(sys.argv[1:])

