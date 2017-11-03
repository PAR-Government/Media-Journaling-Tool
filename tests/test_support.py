import unittest
import os

class TestSupport(unittest.TestCase):

    def locateFile(self, file):
        abspath = os.path.abspath(file)
        height = os.path.abspath(os.path.curdir).count(os.path.sep)
        while not os.path.exists(abspath) and height>0:
            abspath = os.path.abspath(os.path.join('..',file))
            height-=1
        return abspath


