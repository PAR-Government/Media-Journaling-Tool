from maskgen import scenario_model
import unittest
from test_support import TestSupport
import csv

from maskgen.plugins import loadPlugins
class TestScenarioModel(TestSupport):

   def test_link_tool(self):
      loadPlugins()
      model = scenario_model.loadProject(self.locateFile('images/sample.json'))
      model.mediaFromPlugin('OutputPNG::Foo')
      lt = model.getLinkTool('sample','orig_input')
      self.assertTrue(isinstance(lt,scenario_model.ImageImageLinkTool))
      mask, analysis,errors = lt.compareImages('sample','orig_input',model,'OutputPng')
      self.assertTrue(len(errors) == 0)
      self.assertTrue('exifdiff' in analysis)
      self.addFileToRemove('test_sm.csv')
      model.toCSV('test_sm.csv',['arguments.purpose','arguments.subject'])
      foundPasteSplice = False
      with open('test_sm.csv', 'rb') as fp:
         reader = csv.reader(fp)
         for row in reader:
            self.assertEqual(6, len(row))
            if row[3] == 'PasteSplice':
               foundPasteSplice = True
               self.assertEqual('sample', row[0])
               self.assertEqual('orig_input', row[1])
               self.assertEqual('input_mod_1', row[2])
               self.assertEqual('add', row[4])
               self.assertEqual('man-made object',row[5])
      self.assertTrue(foundPasteSplice)


   def test_video_add_tool(self):
      from maskgen.scenario_model import VideoAddTool
      tool = VideoAddTool()
      meta = tool.getAdditionalMetaData(self.locateFile('tests/videos/sample1.mov'))
      self.assertEqual((640,480),meta['shape'])
      self.assertEqual('yuv420p',meta['media'][0]['pix_fmt'])
      self.assertEqual('fltp', meta['media'][1]['sample_fmt'])


if __name__ == '__main__':
    unittest.main()
