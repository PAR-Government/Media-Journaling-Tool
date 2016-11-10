from maskgen import image_graph
import unittest
import os
import shutil
from maskgen.batch import batch_project

class TestBatchProcess(unittest.TestCase):

   def test_run(self):
      if os.path.exists('imageset.txt'):
          os.remove('imageset.txt')
      shutil.rmtree('test_projects')
      os.mkdir('test_projects')
      batchProject = batch_project.loadJSONGraph('tests/batch_process.json')
      batchProject.executeOnce(global_state={'projects' : 'test_projects'})

if __name__ == '__main__':
    unittest.main()
