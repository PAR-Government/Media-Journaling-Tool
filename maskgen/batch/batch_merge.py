import argparse
from functools import partial
from maskgen.batch import *
from maskgen.graph_output import ImageGraphPainter
from maskgen.scenario_model import ImageProjectModel
import sys
from maskgen.loghandling import set_logging_level


class MD5Merge:
    def __init__(self, projects, output=None):
        self.output = output
        self.projects = {}
        self.logger = logging.getLogger('maskgen')
        for p in projects:
            md5 = os.path.splitext(os.path.basename(p))[0]
            if md5 not in self.projects:
                self.projects[md5] = [p]
            else:
                self.projects[md5].append(p)

    def merge(self, project):
        """
        :param project: Project to be merged
        :type project: str
        :return: None
        """
        base = ImageProjectModel(self.projects[project][0])
        base_md5 = os.path.basename(os.path.splitext(self.projects[project][0])[0])
        self.logger.debug("Opening {0} as base for project merging.".format(base_md5))
        for p in self.projects[project][1:]:
            p_md5 = os.path.basename(os.path.splitext(p)[0])
            self.logger.debug("Merging {0} into {1}.".format(p_md5, base_md5))
            proj = ImageProjectModel(p)
            merged = base.mergeProject(proj)
            if merged is not None:
                self.logger.error("Unable to merge {0} into {1}.  {2}".format(p_md5, base_md5, merged))

        if self.output:
            base.saveas(os.path.join(self.output, project))
        else:
            base.save()
        ImageGraphPainter(base.getGraph()).output(os.path.join(base.get_dir(), '_overview_.png'))

    def get_journals(self):
        return self.projects.keys()


class PairingMerge:
    def __init__(self, pairings, project_directories, output=None):
        """
        :param pairings: Path to CSV File containing pairings (from,to)
        """
        from csv import reader
        self.output = output
        self.projects = {}
        self.logger = logging.getLogger('maskgen')
        self.project_directories = project_directories

        with open(pairings, "rb") as f:
            _all_pairs = list(reader(f))
            # dict generator would replace repeat journal targets with last value
            for frm, to in _all_pairs:
                if to in self.projects:
                    self.projects[to].append(frm)
                else:
                    self.projects[to] = [frm]

    def merge(self, project):
        base_path = self._find_project(project)
        if base_path is None:
            raise ValueError("{0} was not found in any project directories".format(project))

        base = ImageProjectModel(base_path)
        base_md5 = os.path.basename(os.path.splitext(project)[0])
        self.logger.debug("Opening {0} as base for project merging.".format(base_md5))
        for p in self.projects[project]:
            p_md5 = os.path.basename(os.path.splitext(p)[0])
            self.logger.debug("Merging {0} into {1}.".format(p_md5, base_md5))
            proj = ImageProjectModel(self._find_project(p))
            merged = base.mergeProject(proj)
            if merged is not None:
                self.logger.error("Unable to merge {0} into {1}.  {2}".format(p_md5, base_md5, merged))

        if self.output:
            base.saveas(os.path.join(self.output, project))
        else:
            base.save()
        ImageGraphPainter(base.getGraph()).output(os.path.join(base.get_dir(), '_overview_.png'))

    def get_journals(self):
        return self.projects.keys()

    def _find_project(self, project_name):
        if os.path.isfile(project_name):
            return project_name
        for p in self.project_directories:
            if os.path.split(p)[1] == project_name + ".json":
                return p


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', default=None, help='Desired location to store merged journals.')
    parser.add_argument('--projects', default=None, help='Comma separated list of directories to merge or file '
                        'of journals that can be merged.', required=True)
    parser.add_argument('--pairs', default=None, help='CSV file of journal MD5s to merge (from,to)')
    parser.add_argument('--completeFile', default=None, help='File listing completed projects.')
    parser.add_argument('--loglevel', type=int, help='Log level')
    parser.add_argument('--workdir', help='Work')
    parser.add_argument('--threads', '-t', default='1', help='Number of threads.')
    args = parser.parse_args(argv)

    if os.path.isfile(args.projects):
        project_files = pick_projects(args.projects)
    else:
        project_files = []
        for d in args.projects.split(","):
            project_files.extend(pick_projects(d))

    if not project_files:
        print("No Project Directories Provided")
        parser.print_help()
        exit(1)

    set_logging_level(logging.INFO if not args.loglevel else args.loglevel)

    merger = MD5Merge(project_files, args.output) if not args.pairs else \
        PairingMerge(args.pairs, project_files, args.output)
    processor = BatchProcessor(args.completeFile, merger.get_journals(), args.threads)
    func = partial(merger.merge)
    processor.process(func)


if __name__ == '__main__':
    main()
