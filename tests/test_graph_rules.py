from maskgen import graph_rules
import unittest
from maskgen.scenario_model import loadProject
from test_support import TestSupport

class TestToolSet(TestSupport):

    def test_aproject(self):
        model = loadProject(self.locateFile('images/sample.json'))
        leafBaseTuple = model.getTerminalAndBaseNodeTuples()[0]
        result = graph_rules.setFinalNodeProperties(model, leafBaseTuple[0])
        self.assertEqual('yes', result['manmade'])
        self.assertEqual('no', result['face'])
        self.assertEqual('no', result['postprocesscropframes'])
        self.assertEqual('no', result['spatialother'])
        self.assertEqual('no', result['otherenhancements'])
        self.assertEqual('yes', result['color'])
        self.assertEqual('no', result['blurlocal'])
        self.assertEqual('large', result['compositepixelsize'])
        self.assertEqual('yes', result['imagecompression'])


if __name__ == '__main__':
    unittest.main()
