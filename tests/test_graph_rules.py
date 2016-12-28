from maskgen import graph_rules
import unittest
from maskgen.scenario_model import ImageProjectModel,loadProject

from maskgen.software_loader import Software,loadOperations,loadProjectProperties,loadSoftware

class TestToolSet(unittest.TestCase):
    def test_aproject(self):
        ops = loadOperations("operations.json")
        soft = loadSoftware("software.csv")
        loadProjectProperties("project_properties.json")
        model = loadProject('images/sample.json')
        leafBaseTuple=  model.getTerminalAndBaseNodeTuples()[0]
        result = graph_rules.setFinalNodeProperties(model,leafBaseTuple[0])
        self.assertEqual('yes', result['manmade'])
        self.assertEqual('no', result['face'])
        self.assertEqual('no', result['postprocesscropframes'])
        self.assertEqual('no', result['spatialother'])
        self.assertEqual('yes', result['otherenhancements'])
        self.assertEqual('yes', result['color'])
        self.assertEqual('no', result['blurlocal'])
        self.assertEqual('small', result['compositepixelsize'])
        self.assertEqual('yes', result['imagecompression'])


if __name__ == '__main__':
    unittest.main()
