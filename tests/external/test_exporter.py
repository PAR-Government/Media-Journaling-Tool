import unittest
from maskgen.external.api import *
from tests.test_support import TestSupport
import os
import numpy as np
import random
from maskgen.external.exporter import ExportManager, DoNothingExportTool
import sys
from threading import Condition
from time import sleep


class SomePausesExportTool:

    def export(self, path, bucket, dir, log):
        for i in range (1,11):
            log ('({}%)'.format(i))
            sleep(1)
        log('DONE {} {}/{}'.format(path,bucket,dir))

def notifier_check(foo=0,bar=0):
    from maskgen import MaskGenLoader
    prefLoader = MaskGenLoader()
    from maskgen.notifiers import getNotifier
    notifiers = getNotifier(prefLoader)
    logging.getLogger('jt_export').info ('status = {}'.format(notifiers.check_status()))
    logging.getLogger('jt_export').info ('foo = {} bar = {}'.format(foo, bar))

class TestExporter(TestSupport):

    def setUp(self):
        self.loader = MaskGenLoader()
        self.condition = Condition()
        self.altenate_directory = os.path.join(os.path.expanduser('~'),'TESTJTEXPORT')
        if not os.path.exists(self.altenate_directory):
            os.makedirs(self.altenate_directory)
        self.exportManager = ExportManager(notifier=self.notify_status,
                                           altenate_directory=self.altenate_directory,
                                           export_tool=DoNothingExportTool)
        self.notified = False
        self.notifications = []
        self.filetoupload = os.path.abspath(self.locateFile('tests/data/classifications.csv'))
        self.what = 'classifications'

    def tearDown(self):
        import shutil
        self.exportManager.shutdown()
        altenate_directory = os.path.join(os.path.expanduser('~'), 'TESTJTEXPORT')
        shutil.rmtree(altenate_directory)

    def notify_status(self,who, when, what):
        print ('export manager notify {} at {} state {}'.format(who,when, what))
        self.notifications.append((who, when, what))
        self.condition.acquire()
        self.notified = what
        self.condition.notifyAll()
        self.condition.release()

    def check_status(self, status='DONE'):
        self.condition.acquire()
        while self.notified != status:
            self.condition.wait()
        self.condition.release()

    def test_export(self):
        self.notifications = []
        self.notified = False
        #foo = "/Users/ericrobertson/Downloads/a81d4ebbf08afab92d864245020298ac.tgz"
        #what = 'a81d4ebbf08afab92d864245020298ac'
        pathname = self.filetoupload
        self.exportManager.upload(pathname, 'medifor/par/journal/shared/',
                                  remove_when_done=False)
        current = self.exportManager.get_all()
        self.assertTrue(self.what in current)
        self.check_status('DONE')
        history = self.exportManager.get_all()
        self.assertTrue(history[self.what][1] == 'DONE')
        with open (os.path.join(self.altenate_directory,'camera_sizes.txt')) as log:
            lines = log.readlines()
            print lines[-2:]
        self.assertTrue('DONE' in lines[-1])
        self.assertTrue('START' in lines[-2])

    def test_export_early_stop(self):
        self.exportManager.export_tool = SomePausesExportTool()
        self.notifications = []
        self.notified = False
        pathname = self.filetoupload
        name = self.exportManager.upload(pathname, 'medifor/par/journal/shared/',
                                  remove_when_done=False)
        self.exportManager.stop(name)
        self.check_status('FAIL')
        self.exportManager.restart(name)
        current = self.exportManager.get_all()
        self.assertTrue(self.what in current)
        self.check_status('DONE')
        history = self.exportManager.get_all()
        self.assertTrue(history[self.what][1] == 'DONE')
        with open (os.path.join(self.altenate_directory,'classifications.txt')) as log:
            lines = log.readlines()
            print lines[-2:]
        self.assertTrue('DONE' in lines[-1])
        self.assertTrue('START' in lines[0])

    def test_slow_export(self):
        self.notified = False
        self.exportManager.export_tool = SomePausesExportTool()
        #foo = "/Users/ericrobertson/Downloads/a81d4ebbf08afab92d864245020298ac.tgz"
        #what = 'a81d4ebbf08afab92d864245020298ac'
        pathname = self.filetoupload
        self.exportManager.upload(pathname, 'medifor/par/journal/shared/',remove_when_done=False)
        current = self.exportManager.get_all()
        self.assertTrue(self.what in current)
        self.check_status()
        history = self.exportManager.get_all()
        self.assertTrue(history[self.what][1] == 'DONE')
        self.assertTrue(len(self.notifications) >= 12)
        self.notifications = []

    def test_export_sync(self):
        self.notifications = []
        self.notified = False
        # foo = "/Users/ericrobertson/Downloads/a81d4ebbf08afab92d864245020298ac.tgz"
        # what = 'a81d4ebbf08afab92d864245020298ac'
        pathname = self.filetoupload
        self.exportManager.sync_upload(pathname, 'medifor/par/journal/shared/', remove_when_done=False)
        history = self.exportManager.get_all()
        self.assertTrue(history[self.what][1] == 'DONE')


if __name__ == '__main__':
    unittest.main()
