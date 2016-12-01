from maskgen import scenario_model
import unittest

class TestScenarioModel(unittest.TestCase):

   def test_link_tool(self):
      model = scenario_model.loadProject('images/sample.json')
      lt = model.getLinkTool('sample','orig_input')
      self.assertTrue(isinstance(lt,scenario_model.ImageImageLinkTool))
      maskname,mask, analysis,errors = lt.compareImages('sample','orig_input',model,'OutputPNG')
      self.assertTrue(len(errors) == 0)
      self.assertTrue('exifdiff' in analysis)
      model.constructCompositesAndDonors()
      model.toCSV('test.csv',['arguments.purpose','arguments.subject'])


if __name__ == '__main__':
    unittest.main()
