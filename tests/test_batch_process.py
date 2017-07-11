from maskgen import image_graph
import unittest
import os
import shutil
from maskgen.batch import batch_project
from threading import Lock

class TestBatchProcess(unittest.TestCase):


   def test_run(self):
      if os.path.exists('imageset.txt'):
          os.remove('imageset.txt')
      with open ('imageset.txt','w') as fp:
          fp.writelines([ filename + os.linesep for filename in os.listdir('tests/images') if not filename.startswith('test_project')])
      if os.path.exists('test_projects'):
          shutil.rmtree('test_projects')
      os.mkdir('test_projects')
      batch_project.loadCustomFunctions()
      batchProject = batch_project.loadJSONGraph('tests/batch_process.json')
      global_state = {
          'projects': 'test_projects',
          'project': batchProject,
          'picklists_files': {},
          'picklistlock': Lock(),
          'count': batch_project.IntObject(20)
      }
      for i in range(2):
          batchProject.executeOnce(global_state)

if __name__ == '__main__':
    unittest.main()
