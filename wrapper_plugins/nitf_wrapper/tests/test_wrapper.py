import unittest

from nitf_wrapper import opener


class TestToolSet(unittest.TestCase):

    def __init__(self,methodName='runTest'):
        unittest.TestCase.__init__(self,methodName=methodName)

    def test_opener(self):
        opener.openNTFFile('2aa5cdc0272a4b299f0c1318b04867d3.ntf')

if __name__ == '__main__':
    unittest.main()
