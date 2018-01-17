from __future__ import print_function
import argparse
from maskgen import scenario_model
from maskgen.software_loader import *
import bulk_export
from maskgen import graph_rules
import csv
import os
from maskgen.batch import pick_projects


def validate_export(error_writer,project, sm):
    """
    Save error report, project properties, composites, and donors
    :param sm: scenario model
    """
    errorList = sm.validate()
    name = os.path.basename(project)
    graph_rules.processProjectProperties(sm)
    sm.save()
    for err in errorList:
        error_writer.writerow((name, str(err)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projects', help='Directory of projects')
    args = parser.parse_args()

    graph_rules.setup()

    project_list = pick_projects(args.projects)

    with open(os.path.join(args.projects,'ErrorReport_' + str(os.getpid()) + '.csv'), 'wb') as csvfile:
        error_writer = csv.writer(csvfile, delimiter = ' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for project in project_list:
            try:
                validate_export(error_writer, project, scenario_model.loadProject(project))
            except Exception as e:
                print (project)
                print (str(e))

if __name__ == '__main__':
    main()
