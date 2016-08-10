import argparse

import scenario_model
from software_loader import *
import bulk_export
import graph_rules
import csv
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projectDir', help='Directory of projects')
    args = parser.parse_args()

    ops = loadOperations("operations.json")
    soft = loadSoftware("software.csv")

    graph_rules.setup()

    projectList = bulk_export.pick_dirs(args.projectDir)

    with open(os.path.join(args.projectDir,'ErrorReport.csv'), 'wb') as csvfile:
        errorWriter = csv.writer(csvfile, delimiter = ' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for project in projectList:
            name = os.path.basename(project)
            sm = scenario_model.ProjectModel(os.path.join(project, name + '.json'))
            errorList = sm.validate()
            for err in errorList:
                errorWriter.writerow((name, str(err)))


if __name__ == '__main__':
    main()