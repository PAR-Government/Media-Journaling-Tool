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

    def tearDown(self):
        import shutil
        altenate_directory = os.path.join(os.path.expanduser('~'), 'TESTJTEXPORT')
        shutil.rmtree(altenate_directory)

    def notify_status(self,who, when, what):
        print ('export manager notify {} at {} state {}'.format(who,when, when))
        self.notifications.append((who, when, what))
        self.condition.acquire()
        self.notified = what == 'DONE'
        self.condition.notifyAll()
        self.condition.release()

    def check_status(self):
        self.condition.acquire()
        while not self.notified:
            self.condition.wait()
        self.condition.release()

    def test_export(self):
        self.notifications = []
        self.notified = False
        #foo = "/Users/ericrobertson/Downloads/a81d4ebbf08afab92d864245020298ac.tgz"
        #what = 'a81d4ebbf08afab92d864245020298ac'
        what = 'camera_sizes'
        pathname = self.locateFile('tests/data/camera_sizes.json')
        self.exportManager.upload(pathname, 'medifor/par/journal/shared/',remove_when_done=False)
        current = self.exportManager.get_current()
        self.assertTrue(what in current)
        self.check_status()
        history = self.exportManager.get_history()
        self.assertTrue(history[what][1] == 'DONE')

    def test_slow_export(self):
        self.notified = False
        self.exportManager.export_tool = SomePausesExportTool()
        #foo = "/Users/ericrobertson/Downloads/a81d4ebbf08afab92d864245020298ac.tgz"
        #what = 'a81d4ebbf08afab92d864245020298ac'
        what = 'camera_sizes'
        pathname = self.locateFile('tests/data/camera_sizes.json')
        self.exportManager.upload(pathname, 'medifor/par/journal/shared/',remove_when_done=False)
        current = self.exportManager.get_current()
        self.assertTrue(what in current)
        self.check_status()
        history = self.exportManager.get_history()
        self.assertTrue(history[what][1] == 'DONE')
        self.assertTrue(len(self.notifications) == 13)
        self.notifications = []

    def test_export_sync(self):
        self.notifications = []
        self.notified = False
        # foo = "/Users/ericrobertson/Downloads/a81d4ebbf08afab92d864245020298ac.tgz"
        # what = 'a81d4ebbf08afab92d864245020298ac'
        what = 'camera_sizes'
        pathname = self.locateFile('tests/data/camera_sizes.json')
        self.exportManager.sync_upload(pathname, 'medifor/par/journal/shared/', remove_when_done=False)
        history = self.exportManager.get_history()
        self.assertTrue(history[what][1] == 'DONE')


if __name__ == '__main__':
    unittest.main()
