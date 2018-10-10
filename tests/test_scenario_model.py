from maskgen import scenario_model
import unittest
from test_support import TestSupport
from maskgen.support import getPathValuesFunc
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
      model.toCSV('test_sm.csv',[getPathValuesFunc('arguments.purpose'),getPathValuesFunc('arguments.subject')])
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


   def test_video_video_link_tool(self):
      from maskgen.scenario_model import VideoVideoLinkTool
      from maskgen.software_loader import Operation
      from mock import Mock
      from maskgen.video_tools import get_end_frame_from_segment, get_file_from_segment
      from maskgen.image_wrap import ImageWrapper
      import os
      import numpy as np
      def create_zero(h,w):
         return ImageWrapper(np.zeros((h,w),dtype='uint8'))
      vida = self.locateFile('videos/sample1.mov')
      vidb= self.locateFile('videos/sample1_swap.mov')
      image_values = {'a': (create_zero(300,300),vida), 'b': (create_zero(300,300),vidb)}
      def get_image(arg):
         return image_values[arg]
      tool = VideoVideoLinkTool()
      scModel = Mock()
      scModel.gopLoader = Mock()
      scModel.G.dir = '.'
      scModel.gopLoader.getOperationWithGroups = Mock(return_value = Operation(name='test', category='test'))
      scModel.getImageAndName = get_image
      mask,analysis,errors = tool.compareImages('a', 'b', scModel, 'Normalization',
                                                arguments={},
                                                analysis_params={})
      self.assertEqual(0,len(errors))
      self.assertEqual((640,480),mask.size)
      self.assertEqual(1, len (analysis['videomasks']))
      self.assertEqual(803, get_end_frame_from_segment(analysis['videomasks'][0]))
      self.assertTrue(os.path.exists(get_file_from_segment(analysis['videomasks'][0])))


   def test_video_add_tool(self):
      from maskgen.scenario_model import VideoAddTool
      tool = VideoAddTool()
      meta = tool.getAdditionalMetaData(self.locateFile('tests/videos/sample1.mov'))
      self.assertEqual((640,480),meta['shape'])
      self.assertEqual('yuv420p',meta['media'][0]['pix_fmt'])
      self.assertEqual('fltp', meta['media'][1]['sample_fmt'])


   def test_getDonorAndBaseNodeTuples(self):
      model = scenario_model.loadProject(self.locateFile('images/sample.json'))
      r = model.getDonorAndBaseNodeTuples()
      for t in r:
         if ((u'hat_splice_crop', u'input_mod_1'), u'hat', [u'hat_splice_crop', u'hat_splice_rot_1', u'hat_splice', u'hat']) == t:
            return
      self.assertTrue(False,'Should not be here')


if __name__ == '__main__':
    unittest.main()
