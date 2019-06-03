import unittest
import os
import shutil

class TestSupport(unittest.TestCase):

    def remove_files(self):
        for file in self.files_to_remove:
            if os.path.exists(file):
                if os.path.isdir(file):
                    shutil.rmtree(file)
                else:
                    os.remove(file)

    def __init__(self,methodName='runTest'):
        self.files_to_remove = []
        unittest.TestCase.__init__(self, methodName=methodName)
        self.addCleanup(
            self.remove_files
        )

    def addFileToRemove(self,filename, preemptive=False):
        self.files_to_remove.append(filename)
        if preemptive and os.path.exists(filename):
            if os.path.isdir(filename):
                shutil.rmtree(filename)
            else:
                os.remove(filename)

    def locateFile(self, file):
        abspath = os.path.abspath(file)
        curdir = os.path.abspath(os.path.curdir)
        height = curdir.count(os.path.sep)
        while not os.path.exists(abspath) and height>0:
            curdir = os.path.dirname(curdir)
            abspath = os.path.abspath(os.path.join(curdir,file))
            height-=1
        return abspath


