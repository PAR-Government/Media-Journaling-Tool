from maskgen import image_graph
import unittest
import os
import shutil
from maskgen.batch import batch_project
from maskgen.batch.batch_process import processSpecification
from maskgen.batch.permutations import *
from threading import Lock
try:
    from maskgen_coco import moveValidImages, createBatchProjectGlobalState


    class TestBatchProcess(unittest.TestCase):

        def setUp(self):
            if os.path.exists('test_coco_images'):
                shutil.rmtree('test_coco_images')
            if os.path.exists('test_coco_imageset.txt'):
                os.remove('test_coco_imageset.txt')
            shutil.copytree('tests/other_plugins/CocoMaskSelector/test_coco_images','test_coco_images')
            open('test_coco_imageset.txt','w').close()
            #moveValidImages('test_coco_images','test_coco_images',
            #                'tests/other_plugins/CocoMaskSelector/annotations.json',maxCount=10)

        def test_run(self):
            if os.path.exists('test_coco_projects'):
                shutil.rmtree('test_coco_projects')
            os.mkdir('test_coco_projects')
            batch_project.loadCustomFunctions()
            batchProject = batch_project.loadJSONGraph('tests/other_plugins/CocoMaskSelector/batch_process.json')
            global_state = {
                'projects': 'test_coco_projects',
                'project': batchProject,
                'picklists_files': {},
                'workdir': '.',
                'coco.annotations':'tests/other_plugins/CocoMaskSelector/annotations.json',
                'count': batch_project.IntObject(20),
                'permutegroupsmanager': PermuteGroupManager()
            }
            global_state.update(createBatchProjectGlobalState(global_state))
            batchProject.loadPermuteGroups(global_state)
            batchProject.executeOnce(global_state)


    if __name__ == '__main__':
        unittest.main()
except ImportError as e:
    log = logging.getLogger('maskgen')
    log.warning("Maskgen Coco not installed")


