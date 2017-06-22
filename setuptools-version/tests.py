from setuptools_maskgen_version import format_version,get_version
import unittest


class Test(unittest.TestCase):

    def test_git_describe(self):
        print get_version()
        assert format_version('ca0be43') == 'ca0be43'