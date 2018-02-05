import os
import csv
import sys
import logging
from threading import RLock, Thread

def pick_projects(directory):
    """
    Finds all subdirectories in directory containing a .json file
    :param directory: string containing directory of subdirectories to search
    :return: list projects found under the given directory
    """
    ext = '.json'
    subs = [x[0] for x in os.walk(directory,followlinks=True)]
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

    def __init__(self, completeFile, itemsToProcess, threads=1):
        self.completefile = completeFile if completeFile is not None else str(os.getpid()) + '.txt'
        self.itemsToProcess = itemsToProcess
        self.threads=threads
        self.count = 0
        self.lock = RLock()

    def _thread_worker(self, total, func_to_run,done_file,error_writer):
        while not self.q.empty():
            try:
                item_to_process = self.q.get_nowait()
                if item_to_process is None:
                    break
                item_id = item_to_process[0] if isinstance(item_to_process,tuple) else item_to_process
                logging.getLogger('maskgen').info('Project updating: ' + str(item_id))
                errors = func_to_run(item_to_process)
                for error in errors:
                    error_writer.write((str(item_id), error))
                with self.lock:
                    self.count += 1
                    logging.getLogger('maskgen').info(
                        'Project updated [' + str(self.count) + '/' + str(total) + '] ' + str(item_id))

                    done_file.write(item_id + '\n')
                    done_file.flush()
            except Exception as e:
                logging.getLogger('maskgen').error(str(e))
                logging.getLogger('maskgen').error('Project skipped: ' + str(item_id))

    def process(self, func):
        from Queue import Queue
        from functools import partial
        skips = []
        if  os.path.exists(self.completefile):
            with open(self.completefile, 'r') as skip:
                skips = skip.readlines()
            skips = [x.strip() for x in skips]
        count = 0
        total = len(self.itemsToProcess)
        logging.getLogger('maskgen').info('Processing {} projects'.format(total))
        name=0
        threads=[]
        self.q = Queue()
        for item_to_process in self.itemsToProcess:
            if item_to_process not in skips:
                self.q.put(item_to_process)
        with open(self.completefile, 'a') as done_file:
            with open(os.path.join('ErrorReport_' + str(os.getpid()) + '.csv'), 'w') as csvfile:
                error_writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                thread_func = partial(self._thread_worker, total, func, done_file, error_writer)
                for i in range(int(self.threads)):
                    name += 1
                    t = Thread(target=thread_func, name=str(name))
                    threads.append(t)
                    t.start()
                for thread in threads:
                    thread.join()
        return self.count
