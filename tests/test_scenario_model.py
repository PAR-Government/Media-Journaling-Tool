from maskgen import scenario_model
import unittest
from maskgen.graph_rules import Jpeg2000CompositeBuilder,ColorCompositeBuilder
class TestScenarioModel(unittest.TestCase):

   def test_link_tool(self):
      model = scenario_model.loadProject('images/sample.json')
      lt = model.getLinkTool('sample','orig_input')
      self.assertTrue(isinstance(lt,scenario_model.ImageImageLinkTool))
      mask, analysis,errors = lt.compareImages('sample','orig_input',model,'OutputPNG')
      self.assertTrue(len(errors) == 0)
      self.assertTrue('exifdiff' in analysis)
      model.constructCompositesAndDonors()
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

if __name__ == '__main__':
    unittest.main()
