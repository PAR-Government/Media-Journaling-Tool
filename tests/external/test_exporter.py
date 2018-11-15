import unittest
from maskgen.external.api import *
from tests.test_support import TestSupport
import os
import numpy as np
import random
from maskgen.external.exporter import ExportManager, DoNothingExportTool
import sys
from threading import Condition

class TestExporter(TestSupport):

    def setUp(self):
        self.loader = MaskGenLoader()
        self.condition = Condition()
        altenate_directory = os.path.join(os.path.expanduser('~'),'TESTJTEXPORT')
        if not os.path.exists(altenate_directory):
            os.makedirs(altenate_directory)
        self.exportManager = ExportManager(notifier=self.notify_status,
                                           altenate_directory=altenate_directory,
                                           export_tool=DoNothingExportTool)
        self.notified = False

    def tearDown(self):
        import shutil
        altenate_directory = os.path.join(os.path.expanduser('~'), 'TESTJTEXPORT')
        shutil.rmtree(altenate_directory)

    def notify_status(self,who,what):
        print ('export manager notify ' + who + ' ' + what)
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

    def test_export_sync(self):
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
