from __future__ import print_function
import time
import logging
from logging import handlers, config
import os


class MaskGenTimedRotatingFileHandler(handlers.TimedRotatingFileHandler):
    """
    Always roll-over if it is a new day, not just when the process is active
    """
    forceRotate = False
    def __init__(self, filename):
        if os.path.exists(filename):
            yesterday = time.strftime("%Y-%m-%d", time.gmtime(int(os.stat(filename).st_ctime)))
            today = time.strftime("%Y-%m-%d", time.gmtime(time.time()))
            self.forceRotate = (yesterday != today)
        handlers.TimedRotatingFileHandler.__init__(self,filename, when='D', interval=1, utc=True)

    def shouldRollover(self, record):
        """
                Determine if rollover should occur

                record is not used, as we are just comparing times, but it is needed so
                the method siguratures are the same
                """
        t = int(time.time())
        if t >= self.rolloverAt or self.forceRotate:
            self.forceRotate = False
            return 1
        return 0

def set_logging_level(level):
    for handler in logging.getLogger('maskgen').handlers:
        handler.setLevel(level)

def set_logging(directory=None, filename='maskgen.log'):
    logger = logging.getLogger('maskgen')
    logger.setLevel(logging.INFO)

    for handler in logger.handlers:
        logger.removeHandler(handler)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s[%(threadName)s]- %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    dir = directory if directory is not None and os.path.isdir(directory) else '.'
    logfile = os.path.join(os.getenv("HOME"),filename) if not os.access(dir,os.W_OK) else os.path.join(dir,filename)

    fh = MaskGenTimedRotatingFileHandler(logfile)

    fh.setLevel(logging.INFO)
    # add formatter to ch
    fh.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(fh)

    if os.path.exists('logging.config'):
        print ('Establishing logging configuration from file')
        config.fileConfig('logging.config')


def flush_logging():
    logger = logging.getLogger('maskgen')
    for handler in logger.handlers:
        handler.flush()
