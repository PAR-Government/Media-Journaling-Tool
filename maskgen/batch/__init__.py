import os
import csv
import sys

def pick_projects(directory):
    """
    Finds all subdirectories in directory containing a .json file
    :param directory: string containing directory of subdirectories to search
    :return: list projects found under the given directory
    """
    ext = '.json'
    subs = [x[0] for x in os.walk(directory)]
    projects = []

    for sub in subs:
        files = []
        for f in os.listdir(sub):
            if f.endswith(ext):
                files.append(f)
        if len(files) > 0:
            sizes = [os.stat(os.path.join(sub, pick)).st_size for pick in files]
            max_size = max(sizes)
            index = sizes.index(max_size)
            projects.append(os.path.join(sub, files[index]))
    return projects

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

class BatchProcessor:

    def __init__(self, completeFile, itemsToProcess):
        self.completefile = completeFile if completeFile is not None else str(os.getpid()) + '.txt'
        self.itemsToProcess = itemsToProcess

    def process(self, func):
        skips = []
        if  os.path.exists(self.completefile):
            with open(self.completefile, 'r') as skip:
                skips = skip.readlines()
            skips = [x.strip() for x in skips]
        count = 0
        total = len(self.itemsToProcess)
        with open(self.completefile, 'a') as done_file:
            with open(os.path.join('ErrorReport_' + str(os.getpid()) + '.csv'), 'w') as csvfile:
                error_writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                for item_to_process in self.itemsToProcess:
                    try:
                        if item_to_process in skips:
                            count += 1
                            continue
                        print 'Project updating: ' + item_to_process
                        errors = func(item_to_process)
                        for error in errors:
                            error_writer.write((item_to_process, error))
                        print 'Project updated [' + str(count) + '/' + str(total) + '] ' + item_to_process
                        done_file.write(item_to_process + '\n')
                        done_file.flush()
                        csvfile.flush()
                    except Exception as e:
                        print e
                        print 'Project skipped: ' + item_to_process
                    sys.stdout.flush()
                    count += 1
        return count
