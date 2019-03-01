import argparse
from functools import partial
from maskgen.batch import *
from maskgen.graph_output import ImageGraphPainter
from maskgen.scenario_model import ImageProjectModel
import sys


projects = {}


def merge(project, output=None):
    base = ImageProjectModel(projects[project][0])
    for p in projects[project][1:]:
        proj = ImageProjectModel(p)
        base.mergeProject(proj)

    if output:
        base.saveas(os.path.join(output, project))
    else:
        base.save()
    ImageGraphPainter(base.getGraph()).output(os.path.join(base.get_dir(), '_overview_.png'))


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', default=None, help='Desired location to store merged journals.')
    parser.add_argument('--projects', '-p', default=None, help='Comma separated list of directories to merge or file '
                        'of journals that can be merged.', required=True)
    parser.add_argument('--completeFile', '-c', default=None, help='File listing completed projects.')
    parser.add_argument('--threads', '-t', default='1', help='Number of threads.')
    args = parser.parse_args(argv)

    if os.path.isfile(args.projects):
        project_files = pick_projects(args.projects)
    else:
        project_files = []
        for d in args.projects.split(","):
            project_files.extend(pick_projects(d))

    global projects
    for p in project_files:
        md5 = os.path.splitext(os.path.basename(p))[0]
        if md5 not in projects:
            projects[md5] = [p]
        else:
            projects[md5].append(p)

    processor = BatchProcessor(args.completeFile, projects.keys(), args.threads)
    func = partial(merge, output=args.output)
    processor.process(func)


if __name__ == '__main__':
    main()
