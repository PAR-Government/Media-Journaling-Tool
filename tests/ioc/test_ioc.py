import unittest
from maskgen.ioc.registry import broker,Method,Attribute,IoCComponent
from tests.test_support import TestSupport


class Bar:
   doer  = IoCComponent('x', Method('dosomething'))
   title = IoCComponent('x', Attribute('title', str))

   def dosomething(self):
       return self.doer()

   def gettitle(self):
       return self.title

class DoerExample:

   def __init__(self,title):
      self.title = title
      broker.register('x',self)

   def dosomething(self):
       return 'do'

class TestIoC(TestSupport):


    def test_ioc(self):
        b = Bar()
        DoerExample('testtitle')
        self.assertEquals('do',b.dosomething())
        self.assertEquals('testtitle', b.gettitle())


if __name__ == '__main__':
    unittest.main()
