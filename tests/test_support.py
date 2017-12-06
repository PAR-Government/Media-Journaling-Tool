import unittest
import os

class TestSupport(unittest.TestCase):

    def locateFile(self, file):
        abspath = os.path.abspath(file)
        curdir = os.path.abspath(os.path.curdir)
        height = curdir.count(os.path.sep)
        while not os.path.exists(abspath) and height>0:
            curdir = os.path.dirname(curdir)
            abspath = os.path.abspath(os.path.join(curdir,file))
            height-=1
        return abspath


