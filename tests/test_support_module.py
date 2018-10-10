import unittest
import os
import shutil
from test_support import TestSupport
from maskgen.support import getValue, setPathValue

class TestSupportModule(TestSupport):

    def test_get_value(self):
        y = [{},{'z':1}]
        e = {'x': { 'y': y}}
        self.assertEquals(y, getValue(e, 'x.y', None))
        self.assertEquals(1, getValue(e, 'x.y[1].z', None))

    def test_set_value(self):
        y = [{},{'z':1}]
        e = {'x': { 'y': y}}
        setPathValue(e,'x.w',1)
        setPathValue(e,'x.y[1].z',2)
        self.assertEquals(1, getValue(e, 'x.w', None))
        self.assertEquals(2, getValue(e, 'x.y[1].z', None))