import logging
import os
from functools import partial
from multiprocessing import Process, Pipe
from time import sleep

from maskgen.tool_set import S3ProgressPercentage

#-------------------------------------------------------------------------------------------------------------
# Export Tools - export to remote location
#-------------------------------------------------------------------------------------------------------------

class S3ExportTool:

    def __init__(self):
        import boto3
        from boto3.s3.transfer import S3Transfer, TransferConfig
        config = TransferConfig()
        self.s3 = S3Transfer(boto3.client('s3', 'us-east-1'), config)

    def export(self, path, bucket, dir, log):
        self.s3.upload_file(path, bucket, dir + os.path.split(path)[1], callback=S3ProgressPercentage(path, log))

class DoNothingExportTool:

    def export(self, path, bucket, dir, log):
        pass

def _log_and_update_parent(log, pipe_to_parent, message):
    log(message)
    s = message.find('(')
    e = message.find('%')
    pipe_to_parent.send(message[s+1:e])


#-------------------------------------------------------------------------------------------------------------
# Logging Tools - Log files serve is 'historical information', including parsing for status
#
# status is a float percentage or one of START, FAIL, DONE
#-------------------------------------------------------------------------------------------------------------

def _set_logging(directory,name):
    from maskgen.loghandling import set_logging
    logfile = os.path.join(directory,name + '.txt')
    if os.path.exists(logfile):
        os.remove(logfile)
    set_logging(directory, filename=name + '.txt', skip_config=True,logger_name='jt_export')

def _create_stat_file(directory,data):
    with open(os.path.join(directory,'stat.dat'),'w') as fp:
        fp.write(data)

def _get_last_message(pathname):
    try:
        with open(pathname, 'r') as fp:
            return fp.readlines()[-1]
    except:
        return ''

def _get_first_message(pathname):
    try:
        with open(pathname, 'r') as fp:
            return fp.readline().strip()
    except:
        return ''

def _get_status_from_last_message(pathname):
    import re
    msg = _get_last_message(pathname)
    exp = re.compile('.*(DONE|FAIL) (.*) to (.*)')
    match = exp.match(msg)
    if match:
        return match.groups()[0].upper()
    exp = re.compile('.*(\([0-9\.]+%\))')
    match = exp.match(msg)
    if match:
        return float(match.groups()[0][1:-2])
    return 'N/A'

def _get_path_from_first_message(pathname):
    import re
    msg = _get_first_message(pathname)
    exp = re.compile('.*(START) (.*) to (.*)')
    match = exp.match(msg)
    if match is not None:
        return match.groups()
    return None, None, None

#-------------------------------------------------------------------------------------------------------------
# Upload Processing - Child Process UpLoader
#-------------------------------------------------------------------------------------------------------------

def _perform_upload(directory, path, location, pipe_to_parent, remove_when_done , export_tool):

    _set_logging(directory, os.path.splitext(os.path.basename(path))[0])

    bucket = location.split('/')[0].strip()
    dir = location[location.find('/') + 1:].strip()
    dir = dir if dir.endswith('/') else dir + '/'
    logging.getLogger('jt_export').info('START {} to {}'.format(path, location))
    log = partial(_log_and_update_parent, logging.getLogger('jt_export').info, pipe_to_parent)
    try:
        export_tool.export(path, bucket, dir, log)
        logging.getLogger('jt_export').info('DONE {} to {}'.format(path, location))
        pipe_to_parent.send('DONE')
        if remove_when_done:
            os.remove(path)
        _create_stat_file(directory, path)
        pipe_to_parent.close()
    except Exception as e:
        logging.getLogger('jt_export').error(str(e))
        logging.getLogger('jt_export').info('FAIL {} to {}'.format(path, location))
        pipe_to_parent.send('FAIL')
        pipe_to_parent.close()

#-------------------------------------------------------------------------------------------------------------
# External Notifiers -
#-------------------------------------------------------------------------------------------------------------

class ProjectNotifier:
    """
    Used to notify a ImageProjectModel
    """

    def __init__(self, project_sc_model=None):
        self.project_sc_model = project_sc_model

    def __call__(self, pathname, location, message=''):
        self.project_sc_model.notify(self.project_sc_model.getName(),
                                   'export',
                                    location=location,
                                    additional_message=message)

#-------------------------------------------------------------------------------------------------------------
# Active Process Information
#-------------------------------------------------------------------------------------------------------------

class ProcessInfo:

    """
    Active upload process information
    """
    def __init__(self,process,pipe,status='START',location=None,pathname=None,remove_when_done=True):
        self.process = process
        self.pipe = pipe
        self.status = status
        self.pathname = pathname
        self.location = location
        self.remove_when_done=remove_when_done

#-------------------------------------------------------------------------------------------------------------
# Synchronous, in process, uploading
#-------------------------------------------------------------------------------------------------------------

class SyncPipe:

    def __init__(self, sync_process):
        self.sync_process = sync_process
        self.last_message = '0'

    def close(self):
        self.sync_process.update_status('DONE')

    def send(self,*args):
        self.sync_process.update_status(*args)
        self.last_message = args[0]

    def recv(self):
        return self.last_message

    def poll(self,timer):
        sleep(timer)



class SyncProcess:

    def __init__(self, manager, name):
        self.manager = manager
        self.name = name

    def update_status(self,msg):
        self.manager._update_status(self.name, msg)

    def pipe(self):
        return SyncPipe(self)

    def is_alive(self):
        return True

    def terminate(self):
        pass

    def join(self):
        pass

#-------------------------------------------------------------------------------------------------------------
# Core Manager to manage all uploads, kicking off child processes for asynchronous uploads
#-------------------------------------------------------------------------------------------------------------

class ExportManager:

    """
    @type processes: {str: ProcessInfo}
    """
    def __init__(self, notifier=None, altenate_directory=None, queue_size=5, export_tool = S3ExportTool):
        from threading import Lock, Thread, Condition
        self.notifiers = [notifier] if notifier is not None else []
        self.queue_size = queue_size
        #NOTE: not used at the moment.  Did not evaluate to race conditions
        # Intent for queue_wait is to throttle number of active exports
        #self.queue_wait = Condition()
        self.lock = Lock()
        self.processes = {}
        self.directory = os.path.join(os.path.expanduser('~'), 'JTExportLogs') if altenate_directory is None else altenate_directory
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        self.history = {}
        self._load_history()
        self.semaphore  = Condition(self.lock)
        self.listen_thread = Thread(target=self._listen_thread, name='ExportManager.listener')
        self.listen_thread.daemon = True
        self.listen_thread.start()
        self.export_tool = export_tool()
        self.poll_time = 2

    def get_current(self):
        from time import time
        with self.lock:
            return {os.path.splitext(os.path.basename(k))[0]:(time,v.status if v.status is not None else 'START') for k,v in self.processes.iteritems()}

    def _stat_file(self):
        return os.path.join(self.directory,'stat.dat')

    def  _load_history(self):
        self.history = {}
        with self.lock:
            for f in os.listdir(self.directory):
                if f.endswith('.txt'):
                    pathname = os.path.join(self.directory,f)
                    self.history[os.path.splitext(f)[0]] = (os.stat(pathname).st_mtime,
                                                            _get_status_from_last_message(pathname))
        stat_file = self._stat_file()
        if not os.path.exists(stat_file):
            _create_stat_file(self.directory, 'x')
        self.history_date = os.stat(stat_file).st_mtime

    def get_all(self):
        """
        :return: dictionary of name -> (time, message)
        @rtype dict(name, (float, str))
        """
        import copy
        history = copy.copy(self.get_history())
        history.update( self.get_current() )
        return history

    def get_history(self):
        if os.path.exists(self._stat_file()) and os.stat(self._stat_file()).st_mtime != self.history_date:
            self._load_history()
        return self.history

    def _update_status(self, name, msg):
        self.processes[name].status = msg

    def _call_notifier(self, *args):
        for n in self.notifiers:
            n(*args)

    def add_notifier(self, notifier=lambda x, y: True):
        """
        Register external notifier interest in updates
        Notifier is a funciton that accepts a name and status.
        :param notifier:
        :return:
        """
        self.notifiers.append(notifier)

    def remove_notifier(self, notifier=lambda x, y: True):
        """
        Register external notifier interest in updates
        Notifier is a funciton that accepts a name and status.
        :param notifier:
        :return:
        """
        self.notifiers = [n for n in self.notifiers if n !=  notifier]

    def _listen_thread(self):
        """
        List to child process messages on status.
        Track progress and life time of child processes
        :return:
        """
        from copy import copy
        while True:
            self.semaphore.acquire()
            try:
                if len(self.processes) == 0:
                    self.semaphore.wait()
            finally:
                self.semaphore.release()

            processes = copy(self.processes)
            for k, process_info in processes.iteritems():
                if process_info.pipe is not None:
                    try:
                        if process_info.pipe.poll(self.poll_time):
                            process_info.status = process_info.pipe.recv()
                            self._call_notifier(k, process_info.status)
                    except Exception as e:
                        logging.getLogger('maskgen').error("Export Manager upload status check failure {}".format(e.message))
                if process_info.status in ['DONE', 'FAIL'] or not process_info.process.is_alive():
                    try:
                        process_info.process.join()
                    except:
                        pass
                    if process_info.status not in ['DONE', 'FAIL']:
                        process_info.status = 'FAIL'
                    # CALLED OUTSIDE OF LOCK.  LISTENERS MAY WANT TO LOCK, causing a circular block
                    self._call_notifier(k, process_info.status)
                    # self.queue_wait.acquire()
                    # self.queue_wait.notifyAll()
                    # self.queue_wait.release()
            self.semaphore.acquire()
            try:
                self.processes = {k: v for k, v in self.processes.iteritems() if v.status not in [ 'DONE', 'FAIL'] }
            finally:
                self.semaphore.release()

    def restart(self, name):
        """
        Stop Active Process.
        Restart Process.
        Works if the file still is present, even if the prior upload process failed.
        :param name:
        :return:
        """
        pi = self.stop(name)
        if pi is None:
            logfilename = os.path.join(self.directory, name + '.txt')
            status, pathname, location = _get_path_from_first_message(logfilename)
        else:
            pathname = pi.pathname
            location = pi.location
            status = pi.status
        if pathname is None or not os.path.exists(pathname):
            return False
        self.upload(pathname, location)
        return True

    def forget(self, name):
        """
        Stop active upload process if it exists
        Forget the history of the process
        :param name:
        :return:

        """
        self.stop(name)
        logfilename = os.path.join(self.directory, name + '.txt')
        if os.path.exists(logfilename):
            os.remove(logfilename)
        with self.lock:
            if name in self.history:
                self.history.pop(name)

    def stop(self, name):
        """
        Stop active upload process if it exists
        :param name:
        :return:
        @rtype: ProcessInfo
        """
        with self.lock:
            if name in self.processes:
                # ? os.kill(pid, 7)
                self.processes[name].process.terminate()
                return self.processes.pop(name)

    def upload(self, pathname, location, remove_when_done=True):
        """
        Upload file to location in-process asynchonously

        :param pathname:
        :param location:
        :param remove_when_done:
        :return:
        """
        #self.queue_wait.acquire()
        #if self.queue_size == len(self.processes):
        #    self.queue_wait.wait()
        #self.queue_wait.release()
        parent_conn, child_conn = Pipe()
        p = Process(target=_perform_upload,
                    args=(self.directory, os.path.abspath(pathname), location, child_conn, remove_when_done, self.export_tool))
        self.semaphore.acquire()
        try:
            name = os.path.splitext(os.path.basename(pathname))[0]
            self.processes[name] = ProcessInfo(p, parent_conn,
                                                   status='START',
                                                   location=location,
                                                   pathname= os.path.abspath(pathname),
                                                   remove_when_done=remove_when_done)
            if name in self.history:
                self.history.pop(name)
            p.start()
            self.semaphore.notifyAll()
        finally:
            self.semaphore.release()
        logging.getLogger('maskgen').info('START upload {}'.format(name))
        # CALLED OUTSIDE OF LOCK.  LISTENERS MAY WANT TO LOCK, causing a circular block
        self._call_notifier(name, 'START')

    def sync_upload(self, pathname, location, remove_when_done=True):
        """
        Upload file to location in-process
        Block till done
        :param pathname:
        :param location:
        :param remove_when_done:
        :return:
        """
        name = os.path.splitext(os.path.basename(pathname))[0]
        process = SyncProcess(self,name)
        pipe = process.pipe()
        self.semaphore.acquire()
        try:
            self.processes[name] = ProcessInfo(process,
                                               pipe,
                                               status='START',
                                               location=location,
                                               pathname=pathname,
                                               remove_when_done=remove_when_done)
            if name in self.history:
                self.history.pop(name)
            self.semaphore.notifyAll()
        finally:
            self.semaphore.release()
        # CALLED OUTSIDE OF LOCK.  LISTENERS MAY WANT TO LOCK, causing a circular block
        self._call_notifier(name, 'START')
        logging.getLogger('maskgen').info('START synchronous upload {}'.format(name))
        _perform_upload(self.directory, os.path.abspath(pathname), location, pipe, remove_when_done, self.export_tool)









