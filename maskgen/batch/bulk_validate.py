import argparse

from maskgen import scenario_model
from maskgen.software_loader import *
import bulk_export
from maskgen import graph_rules
import csv
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projects', help='Directory of projects')
    args = parser.parse_args()

    loadOperations("operations.json")
    loadSoftware("software.csv")

    graph_rules.setup()

    project_list = bulk_export.pick_projects(args.projectDir)

    with open(os.path.join(args.projectDir,'ErrorReport_' + str(os.getpid()) + '.csv'), 'wb') as csvfile:
        error_writer = csv.writer(csvfile, delimiter = ' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for project in project_list:
            name = os.path.basename(project)
            sm = scenario_model.loadProject(project)
            error_list = sm.validate()
            for err in error_list:
                error_writer.writerow((name, str(err)))

if __name__ == '__main__':
    main()
