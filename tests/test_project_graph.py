from maskgen import tool_set,graph_rules
import unittest
from maskgen import graph_output
import os
import csv
from test_support import TestSupport
from maskgen.support import getPathValuesFunc
import numpy as np

from maskgen.scenario_model import  ImageProjectModel
from maskgen.software_loader import getOperation
from maskgen.graph_rules import processProjectProperties
from maskgen.mask_rules import Jpeg2000CompositeBuilder,ColorCompositeBuilder


class TestToolSet(TestSupport):

    def test_composite(self):
        scModel = ImageProjectModel(self.locateFile('images/sample.json'))
        processProjectProperties(scModel)
        scModel.assignColors()
        probeSet = scModel.getProbeSet(compositeBuilders=[Jpeg2000CompositeBuilder,ColorCompositeBuilder])
        self.assertTrue(len(probeSet) == 2)
        self.assertTrue(len([x for x in probeSet if x.edgeId == ('input_mod_2','input_mod_2_3')]) == 1)
        scModel.toCSV('test_composite.csv',additionalpaths=[getPathValuesFunc('linkcolor'), 'basenode'])
        self.addFileToRemove('test_composite.csv')
        with open('test_composite.csv','rb') as fp:
            reader = csv.reader(fp)
            for row in reader:
                self.assertEqual(6, len(row))
                self.assertTrue(getOperation(row[3]) is not None)
        self.assertTrue(len(probeSet) == 2)
        self.assertTrue('jp2' in probeSet[0].composites)
        self.assertTrue('color' in probeSet[0].composites)
        self.assertTrue('bit number' in probeSet[0].composites['jp2'])
        self.assertTrue('file name' in probeSet[0].composites['jp2'])
        self.assertTrue('color' in probeSet[0].composites['color'])
        self.assertTrue('file name' in probeSet[0].composites['color'])

    def test_composite_extension(self):
        model = ImageProjectModel(self.locateFile('images/sample.json'))
        model.assignColors()
        model.selectEdge('input_mod_1', 'input_mod_2')
        prior_probes = model.getPathExtender().constructPathProbes(start='input_mod_1')
        prior_composite = prior_probes[-1].composites['color']['image']
        new_probes = model.getPathExtender().extendCompositeByOne(prior_probes)
        composite = new_probes[-1].composites['color']['image']
        self.assertTrue(sum(sum(np.all(prior_composite.image_array != [255, 255, 255], axis=2))) -
                        sum(sum(np.all(composite.image_array != [255, 255, 255], axis=2))) < 100)

if __name__ == '__main__':
    unittest.main()
