import unittest

from rawphoto_wrapper import opener


class TestToolSet(unittest.TestCase):

    def __init__(self,methodName='runTest'):
        unittest.TestCase.__init__(self,methodName=methodName)

if __name__ == '__main__':
    unittest.main()
