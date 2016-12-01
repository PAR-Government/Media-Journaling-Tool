from maskgen import tool_set
import unittest
from maskgen import graph_output
import os

from maskgen.software_loader import Software,loadOperations,loadProjectProperties,loadSoftware
from maskgen.plugins import loadPlugins
from maskgen.scenario_model import  ImageProjectModel


class TestToolSet(unittest.TestCase):
    def test_aproject(self):
        ops = loadOperations("operations.json")
        soft = loadSoftware("software.csv")
        loadProjectProperties("project_properties.json")
        loadPlugins()
        scModel = ImageProjectModel('images/sample.json')
        graph_output.ImageGraphPainter(scModel.getGraph()).outputToFile('test_graph_output.png')
        self.assertTrue(os.path.exists('test_graph_output.png'))
        os.remove('test_graph_output.png')

if __name__ == '__main__':
    unittest.main()
