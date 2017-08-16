from maskgen import tool_set,graph_rules
import unittest
from maskgen import graph_output
import os
import csv

from maskgen.scenario_model import  ImageProjectModel
from maskgen.graph_rules import processProjectProperties


class TestToolSet(unittest.TestCase):
    def test_aproject(self):
        scModel = ImageProjectModel('images/sample.json')
        graph_output.ImageGraphPainter(scModel.getGraph()).outputToFile('test_graph_output.png')
        self.assertTrue(os.path.exists('test_graph_output.png'))

    def test_composite(self):
        scModel = ImageProjectModel('images/sample.json')
        processProjectProperties(scModel)
        scModel.assignColors()
        ps = scModel.getProbeSet(compositeBuilders=[graph_rules.Jpeg2000CompositeBuilder])
        self.assertTrue(len(ps) == 1)
        scModel.toCSV('test_composite.csv',additionalpaths=['linkcolor', 'basenode'])
        with open('test_composite.csv','rb') as fp:
            reader = csv.reader(fp)
            for row in reader:
                self.assertEqual(6, len(row))
                self.assertTrue((row[3]!='PasteSplice' and row[4] == '') or (row[3]=='PasteSplice' and row[5] != ''))

    def tearDown(self):
        if os.path.exists('test_composite.csv'):
            os.remove('test_composite.csv')
        if os.path.exists('test_graph_output.png'):
            os.remove('test_graph_output.png')

if __name__ == '__main__':
    unittest.main()
