from maskgen import image_graph
import unittest
import os
import shutil
from maskgen.batch import batch_project
from maskgen import software_loader

class TestBatchProcess(unittest.TestCase):

   def test_run(self):
      if os.path.exists('imageset.txt'):
          os.remove('imageset.txt')
      shutil.copy('tests/imageset.txt','imageset.txt')
      if os.path.exists('test_projects'):
          shutil.rmtree('test_projects')
      os.mkdir('test_projects')
      software_loader.loadOperations("operations.json")
      software_loader.loadSoftware("software.csv")
      software_loader.loadProjectProperties("project_properties.json")
      batchProject = batch_project.loadJSONGraph('tests/batch_process.json')
      batchProject.executeOnce(global_state={'projects' : 'test_projects'})

if __name__ == '__main__':
    unittest.main()
