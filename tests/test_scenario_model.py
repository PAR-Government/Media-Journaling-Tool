from maskgen import scenario_model
import unittest
import numpy as np
from maskgen.mask_rules import Jpeg2000CompositeBuilder, ColorCompositeBuilder
class TestScenarioModel(unittest.TestCase):

   def test_link_tool(self):
      model = scenario_model.loadProject('images/sample.json')
      lt = model.getLinkTool('sample','orig_input')
      self.assertTrue(isinstance(lt,scenario_model.ImageImageLinkTool))
      mask, analysis,errors = lt.compareImages('sample','orig_input',model,'OutputPng')
      self.assertTrue(len(errors) == 0)
      self.assertTrue('exifdiff' in analysis)
      model.toCSV('test.csv',['arguments.purpose','arguments.subject'])

   def test_composite(self):
      model = scenario_model.loadProject('images/sample.json')
      model.assignColors()
      probeSet = model.getProbeSet(compositeBuilders=[ColorCompositeBuilder,Jpeg2000CompositeBuilder])
      self.assertTrue(len(probeSet) == 1)
      self.assertTrue('jp2' in probeSet[0].composites)
      self.assertTrue('color' in probeSet[0].composites)
      self.assertTrue('bit number' in probeSet[0].composites['jp2'])
      self.assertTrue('file name' in probeSet[0].composites['jp2'])
      self.assertTrue('color' in probeSet[0].composites['color'])
      self.assertTrue('file name' in probeSet[0].composites['color'])

   def test_composite_extension(self):
      model = scenario_model.loadProject('images/sample.json')
      model.assignColors()
      model.selectEdge('input_mod_1','input_mod_2')
      prior_probes = model.constructPathProbes(start='input_mod_1')
      prior_composite = prior_probes[-1].composites['color']['image']
      new_probes = model.extendCompositeByOne(prior_probes)
      composite = new_probes[-1].composites['color']['image']
      self.assertTrue(sum(sum(np.all(prior_composite.image_array != [255,255,255],axis=2)))-
                       sum(sum(np.all(composite.image_array != [255, 255, 255], axis=2))) < 100)



if __name__ == '__main__':
    unittest.main()
