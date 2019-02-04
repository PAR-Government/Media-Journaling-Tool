import logging
import os
from functools import partial
from multiprocessing import Process, Pipe
from multiprocessing.forking import  Popen
from time import sleep, time

from maskgen.tool_set import S3ProgressPercentage



class ExportProcess(Process):

    def __init__(self,target, args=[], kwargs={}):
        Process.__init__(self, target=target, name='JTExport',args=args)

#    def start(self):
#        Process.start(self)

class S3ExportTool:

    def export(self, path, bucket, dir, log):
        import boto3
        from boto3.s3.transfer import S3Transfer, TransferConfig
        config = TransferConfig()
        self.s3 = S3Transfer(boto3.client('s3', 'us-east-1'), config)
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

def _is_process_alive(pid):
    import psutil
    try:
        return psutil.Process(pid) is not None
    except:
        return False

def _set_logging(directory,name):
    from maskgen.loghandling import set_logging
    logfile = os.path.join(directory,name + '.txt')
    if os.path.exists(logfile):
        os.remove(logfile)
    set_logging(directory, filename=name + '.txt', skip_config=True,logger_name='jt_export')


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
    return 'START'

def _get_path_from_first_message(pathname):
    import re
    msg = _get_first_message(pathname)
    exp = re.compile('.*(START) (.*) to (.*) on (.*)')
    match = exp.match(msg)
    if match is not None:
        return match.groups()
    raise ValueError('First Message Not Formed')

#-------------------------------------------------------------------------------------------------------------
# Upload Processing - Child Process UpLoader
#-------------------------------------------------------------------------------------------------------------


def _perform_upload(directory, path, location, pipe_to_parent, remove_when_done , export_tool,
                    client_notification=None, client_args=None):

    _set_logging(directory, os.path.splitext(os.path.basename(path))[0])

    bucket = location.split('/')[0].strip()
    dir = location[location.find('/') + 1:].strip()
    dir = dir if dir.endswith('/') else dir + '/'
    logging.getLogger('jt_export').info('START {} to {} on {}'.format(path, location, os.getpid()))
    log = partial(_log_and_update_parent, logging.getLogger('jt_export').info, pipe_to_parent)
    try:
        export_tool.export(path, bucket, dir, log)
        logging.getLogger('jt_export').info('DONE {} to {}'.format(path, location))
        pipe_to_parent.send('DONE')
        if remove_when_done:
            os.remove(path)
        pipe_to_parent.close()
        if client_notification is not None:
            client_notification(**client_args)
    except Exception as e:
        logging.getLogger('jt_export').error(str(e))
        logging.getLogger('jt_export').info('FAIL {} to {}'.format(path, location))
        try:
            pipe_to_parent.send('FAIL')
            pipe_to_parent.close()
        except:
            logging.getLogger('jt_export').error("Child process already disconnected")

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
    def __init__(self,status='START',location=None,pathname=None,name= None,log_file_name=None,remove_when_done=True):
        """

        :param process:
        :param pipe:
        :param status:
        :param location:
        :param pid:
        :param pathname:
        :param name:
        :param remove_when_done:
        """
        self.status = status
        self.pathname = pathname
        self.name = name
        self.location = location
        self.remove_when_done=remove_when_done
        self.log_file_name = log_file_name

    def is_alive(self):
        return False

    def is_active(self):
        return self.status not in ['DONE', 'FAIL']

    def is_owned(self):
        return False

    def get_log_name(self):
        return self.log_file_name

    def _update_process_log(self):
        """

        :param process_inprocessfo:
        :return:
        @type process_info: ProcessInfo
        """
        logfilename = self.get_log_name()
        editmode = 'a+'
        try:
            _get_path_from_first_message(logfilename)
        except:
            editmode='w'
        try:
            with open(logfilename,editmode) as fp:
                if editmode=='w':
                    # overwrite since what was there may be corrupt
                    fp.writelines(['INJECTED MESSAGE START {} to {} on {}\n'.format(self.pathname, self.location, -1)])
                fp.writelines(['INJECTED MESSAGE {} {} to {}\n'.format(self.status,
                                                                     self.pathname,
                                                                     self.location)])
        except Exception as e:
            # ten bucks says windows has a problem here
            logging.getLogger('maskgen').error('Cannot update status of process {}'.format(e.message))

    def getpid(self):
        return os.getpid()

    def _update_dead_process_info_status(self):
        if self.status not in ['DONE', 'FAIL']:
            last_recorded_status = _get_status_from_last_message(
                self.get_log_name())
            if last_recorded_status not in ['DONE', 'FAIL']:
                self.status = 'FAIL'
                self._update_process_log()
            else:
                self.status=last_recorded_status

class OwnedProcessInfo(ProcessInfo):

    def __init__(self, process, pipe, status='START', location=None, pathname=None, name=None,
                 log_file_name=None,remove_when_done=True):
        """

        :param process:
        :param pipe:
        :param status:
        :param location:
        :param pathname:
        :param name:
        :param remove_when_done:
         @type process: Process
        """
        self.process = process
        self.pipe = pipe
        ProcessInfo.__init__(self,
                             status=status,
                             location=location,
                             pathname=pathname,
                             name=name,
                             log_file_name=log_file_name,
                             remove_when_done=remove_when_done
                             )


    def is_alive(self):
        return self.process.is_alive()

    def is_owned(self):
        return True

    def getpid(self):
        return self.process.pid()

    def terminate(self):
        self.process.terminate()

    def update_status(self):
        status_change = False
        try:
            if self.pipe.poll(0.5):
                self.status = self.pipe.recv()
                status_change = True
        except Exception as e:
                logging.getLogger('maskgen').error("Export Manager upload status check failure {}".format(e.message))
        # if we own it, wait for it
        if self.status in ['DONE', 'FAIL'] or not self.is_alive():
            status_change = True
            try:
                self.process.join()
            except:
                pass
            self._update_dead_process_info_status()
        return status_change


class NonOwnedProcessInfo(ProcessInfo):


    def __init__(self,
                 pid=None,
                 status='START',
                 location=None,
                 pathname=None,
                 name=None,
                 log_file_name=None,
                 remove_when_done=True):
        """

        :param process:
        :param pipe:
        :param status:
        :param location:
        :param pathname:
        :param name:
        :param remove_when_done:
         @type process: Process
        """
        self.process_pid = pid
        ProcessInfo.__init__(self,
                             status=status,
                             location=location,
                             pathname=pathname,
                             name=name,
                             log_file_name=log_file_name,
                             remove_when_done=remove_when_done
                             )

    def getpid(self):
        return self.process_pid

    def terminate(self):
        pid = self.getpid()
        if pid is not None:
            try:
                os.kill(int(pid), 9)
            except:
                pass

    def is_owned(self):
        return False

    def is_alive(self):
        return _is_process_alive(self.process_pid) if self.process_pid is not None else False

    def update_status(self):
        old_status = self.status
        self.status = _get_status_from_last_message(self.get_log_name())
        if not self.is_alive() and self.is_active():
            self.status = 'FAIL'
            self._update_process_log()
        return old_status != self.status


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

    def pid(self):
        return os.getpid()

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
    @type processes: dict (str, ProcessInfo)
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
        self._load_history()
        self.semaphore  = Condition(self.lock)
        self.listen_thread = Thread(target=self._listen_thread, name='ExportManager.listener')
        self.listen_thread.daemon = True
        self.listen_thread.start()
        self.export_tool = export_tool()

    def shutdown(self):
        self.semaphore.acquire()
        self.active = False
        self.semaphore.notifyAll()
        self.semaphore.release()
        self.listen_thread.join()

    def  _load_history(self):
        with self.lock:
            for f in os.listdir(self.directory):
                if f.endswith('.txt'):
                    logfilename = os.path.join(self.directory,f)
                    name = os.path.splitext(f)[0]
                    try:
                        status, pathname, location, pid = _get_path_from_first_message(logfilename)
                    except:
                        os.remove(logfilename)
                        continue
                    status = _get_status_from_last_message(logfilename)
                    if name not in self.processes:
                        self.processes[name] = NonOwnedProcessInfo(pid=pid,
                                                                   status=status,
                                                                   location=location,
                                                                   log_file_name=os.path.join(self.directory,
                                                                                              name + '.txt'),
                                                                   pathname=pathname,
                                                                   name=name)

    def get_all(self):
        with self.lock:
            return {k: (time(), v.status if v.status is not None else 'START')
                    for k, v in self.processes.iteritems()}

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
        Notifier is a function that accepts a name and status.
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
        self.active = True
        while self.active:
            sleep_value = 1
            self.semaphore.acquire()
            if not self.active:
                continue
            try:
                active_count = len([p for p in self.processes.values() if p.is_active()])
                if active_count == 0 :
                    sleep_value = 0
                    self.semaphore.wait()
                processes = copy(self.processes)
            finally:
                self.semaphore.release()
            sleep(sleep_value)
            for k, process_info in processes.iteritems():
                if process_info.update_status():
                    self._call_notifier(k, time(), process_info.status)

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
            status, pathname, location, pid = _get_path_from_first_message(logfilename)
            os.remove(logfilename)
        else:
            pathname = pi.pathname
            location = pi.location
            status = pi.status
            os.remove(pi.get_log_name())
        if pathname is None or not os.path.exists(pathname):
            return False

        self.upload(pathname, location, remove_when_done=pi.remove_when_done)
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
            if name in self.processes:
                self.processes.pop(name)

    def stop(self, name):
        """
        Stop active upload process if it exists
        :param name:
        :return:
        @rtype: ProcessInfo
        """
        with self.lock:
            if name in self.processes:
                process_info = self.processes[name]
                process_info.terminate()
                process_info._update_dead_process_info_status()
            else:
                return
        self._call_notifier(name, time(), process_info.status)
        return process_info

    def upload(self, pathname, location, remove_when_done=True, finish_notification=None, finish_notification_args=None):
        """
        Upload file to location in-process asynchonously

        :param pathname:
        :param location:
        :param remove_when_done:
        :return:
        """
        parent_conn, child_conn = Pipe()
        p = ExportProcess(target=_perform_upload,
                    args=(self.directory,
                          os.path.abspath(pathname),
                          location, child_conn,
                          remove_when_done,
                          self.export_tool,
                          finish_notification,
                          finish_notification_args))

        self.semaphore.acquire()
        try:
            name = os.path.splitext(os.path.basename(pathname))[0]
            self.processes[name] = OwnedProcessInfo(p,
                                                    parent_conn,
                                                    status='START',
                                                    location=location,
                                                    pathname = os.path.abspath(pathname),
                                                    name = name,
                                                    log_file_name=os.path.join(self.directory, name + '.txt'),
                                                    remove_when_done=remove_when_done)
            p.start()
            self.semaphore.notifyAll()
        finally:
            self.semaphore.release()
        logging.getLogger('maskgen').info('START upload {}'.format(name))
        # CALLED OUTSIDE OF LOCK.  LISTENERS MAY WANT TO LOCK, causing a circular block
        self._call_notifier(name, time(), 'START')
        return name

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
            self.processes[name] = OwnedProcessInfo(process,
                                               pipe,
                                               status='START',
                                               location=location,
                                               pathname=pathname,
                                               name=name,
                                               log_file_name=os.path.join(self.directory,name + '.txt'),
                                               remove_when_done=remove_when_done)
            self.semaphore.notifyAll()
        finally:
            self.semaphore.release()
        # CALLED OUTSIDE OF LOCK.  LISTENERS MAY WANT TO LOCK, causing a circular block
        self._call_notifier(name, time(), 'START')
        logging.getLogger('maskgen').info('START synchronous upload {}'.format(name))
        _perform_upload(self.directory, os.path.abspath(pathname), location, pipe, remove_when_done, self.export_tool)






