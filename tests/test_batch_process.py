from maskgen import image_graph
import unittest
import os
import shutil
from maskgen.batch import batch_project
from threading import Lock

class TestBatchProcess(unittest.TestCase):

   def test_picker(self):
       global_state = {'iteratorslock': Lock(),
                    'picklistlock': Lock()}
       local_state = {}
       spec = {"type" : "int[5:11]", 'increment':2, 'iterate':'yes'}
       self.assertEqual(5,batch_project.executeParamSpec('test_int_spec',spec,
                                                         global_state,local_state, 'test_node',[]))
       self.assertEqual(7, batch_project.executeParamSpec('test_int_spec', spec,
                                                          global_state, local_state, 'test_node', []))
       self.assertEqual(9, batch_project.executeParamSpec('test_int_spec', spec,
                                                          global_state, local_state, 'test_node', []))
       self.assertEqual(11, batch_project.executeParamSpec('test_int_spec', spec,
                                                          global_state, local_state, 'test_node', []))
       self.assertEqual(5, batch_project.executeParamSpec('test_int_spec', spec,
                                                          global_state, local_state, 'test_node', []))
       spec = {"type": "float[5.1:7]", 'increment': 0.5, 'iterate': 'yes'}
       self.assertEqual(5.1, batch_project.executeParamSpec('test_float_spec', spec,
                                                          global_state, local_state, 'test_node', []))
       self.assertEqual(5.6, batch_project.executeParamSpec('test_float_spec', spec,
                                                          global_state, local_state, 'test_node', []))
       self.assertEqual(6.1, batch_project.executeParamSpec('test_float_spec', spec,
                                                          global_state, local_state, 'test_node', []))
       self.assertEqual(6.6, batch_project.executeParamSpec('test_float_spec', spec,
                                                          global_state, local_state, 'test_node', []))
       self.assertEqual(5.1, batch_project.executeParamSpec('test_float_spec', spec,
                                                          global_state, local_state, 'test_node', []))
       spec = {"type": "list", 'values': ['1','2','3'], 'iterate': 'yes'}
       self.assertEqual('1', batch_project.executeParamSpec('test_list_spec', spec,
                                                            global_state, local_state, 'test_node', []))
       self.assertEqual('2', batch_project.executeParamSpec('test_list_spec', spec,
                                                            global_state, local_state, 'test_node', []))
       self.assertEqual('3', batch_project.executeParamSpec('test_list_spec', spec,
                                                            global_state, local_state, 'test_node', []))
       self.assertEqual('1', batch_project.executeParamSpec('test_list_spec', spec,
                                                            global_state, local_state, 'test_node', []))

   def xtest_run(self):
      if os.path.exists('imageset.txt'):
          os.remove('imageset.txt')
      shutil.copy('tests/data/imageset.txt','imageset.txt')
      if os.path.exists('test_projects'):
          shutil.rmtree('test_projects')
      os.mkdir('test_projects')
      batch_project.loadCustomFunctions()
      batchProject = batch_project.loadJSONGraph('tests/batch_process.json')
      batchProject.executeOnce(global_state={
          'projects' : 'test_projects',
          'picklists_files': {},
          'picklistlock':Lock()
      })

if __name__ == '__main__':
    unittest.main()
