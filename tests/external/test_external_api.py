import unittest
from maskgen.external.api import *
from tests.test_support import TestSupport
import os
import numpy as np
import random
from maskgen.maskgen_loader import MaskGenLoader
import sys


class TestExternalAPI(TestSupport):

    loader = MaskGenLoader()

    def setUp(self):
        self.loader.load()

    def test_pull(self):
        token = self.loader.get_key('apitoken')
        url = self.loader.get_key('apiurl')
        params = {}
        params['width'] = 2180
        #params['high_provenance'] =
        params['media_type'] = 'video'
        findAndDownloadImage(token,url,params,'.',prefix='videos')

if __name__ == '__main__':
    unittest.main()
