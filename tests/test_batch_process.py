from maskgen import image_graph
import unittest
import os
import shutil
from maskgen.batch import batch_project
from maskgen.batch.batch_process import processSpecification
from maskgen.batch.permutations import *
from threading import Lock


class TestBatchProcess(unittest.TestCase):
    def test_int_picker(self):
        manager = PermuteGroupManager()
        global_state = {'iteratorslock': Lock(),
                        'permutegroupsmanager': manager}
        local_state = {}
        spec = {"type": "int[5:11:2]", 'permutegroup': 'yes'}
        manager.next()
        self.assertEqual(5, batch_project.executeParamSpec('test_int_spec', spec,
                                                           global_state, local_state, 'test_node', []))
        manager.next()
        self.assertEqual(7, batch_project.executeParamSpec('test_int_spec', spec,
                                                           global_state, local_state, 'test_node', []))
        manager.next()
        self.assertEqual(9, batch_project.executeParamSpec('test_int_spec', spec,
                                                           global_state, local_state, 'test_node', []))
        manager.next()
        self.assertEqual(11, batch_project.executeParamSpec('test_int_spec', spec,
                                                            global_state, local_state, 'test_node', []))

    def test_float_picker(self):
        manager = PermuteGroupManager()
        global_state = {'iteratorslock': Lock(),
                        'permutegroupsmanager': manager}
        local_state = {}
        spec = {"type": "float[5.1:7:0.5]", 'permutegroup': 'yes'}
        manager.next()
        self.assertEqual(5.1, batch_project.executeParamSpec('test_float_spec', spec,
                                                             global_state, local_state, 'test_node', []))
        manager.next()
        self.assertEqual(5.6, batch_project.executeParamSpec('test_float_spec', spec,
                                                             global_state, local_state, 'test_node', []))
        manager.next()
        self.assertEqual(6.1, batch_project.executeParamSpec('test_float_spec', spec,
                                                             global_state, local_state, 'test_node', []))
        manager.next()
        self.assertEqual(6.6, batch_project.executeParamSpec('test_float_spec', spec,
                                                             global_state, local_state, 'test_node', []))

    def test_list_picker(self):
        manager = PermuteGroupManager()
        global_state = {'iteratorslock': Lock(),
                        'permutegroupsmanager': manager}
        local_state = {}
        spec = {"type": "list", 'values': ['1', '2', '3']}
        self.assertTrue(batch_project.executeParamSpec('test_list_spec', spec,
                                                       global_state, local_state, 'test_node', []) in ['1', '2', '3'])
        self.assertTrue(batch_project.executeParamSpec('test_list_spec', spec,
                                                       global_state, local_state, 'test_node', []) in ['1', '2', '3'])
        self.assertTrue(batch_project.executeParamSpec('test_list_spec', spec,
                                                       global_state, local_state, 'test_node', []) in ['1', '2', '3'])
        self.assertTrue(batch_project.executeParamSpec('test_list_spec', spec,
                                                       global_state, local_state, 'test_node', []) in ['1', '2', '3'])

    def test_extend(self):
        batch_project.loadCustomFunctions()
        import shutil
        shutil.copytree('./images','./testimages')
        self.assertTrue(processSpecification('tests/batch_extension_process.json','','./testimages') == 1)
        shutil.rmtree('./testimages')

    def test_run(self):
        if os.path.exists('imageset.txt'):
            os.remove('imageset.txt')
        with open('imageset.txt', 'w') as fp:
            fp.writelines([filename + os.linesep for filename in os.listdir('tests/images') if
                           not filename.startswith('test_project')])
        if os.path.exists('test_projects'):
            shutil.rmtree('test_projects')
        os.mkdir('test_projects')
        batch_project.loadCustomFunctions()
        batchProject = batch_project.loadJSONGraph('tests/batch_process.json')
        global_state = {
            'projects': 'test_projects',
            'project': batchProject,
            'picklists_files': {},
            'workdir': '.',
            'count': batch_project.IntObject(20),
            'permutegroupsmanager': PermuteGroupManager()
        }
        batchProject.loadPermuteGroups(global_state)
        for i in range(2):
            batchProject.executeOnce(global_state)
        try:
            global_state['permutegroupsmanager'].next()
            self.assertFalse(global_state['permutegroupsmanager'].hasNext())
            global_state['permutegroupsmanager'].next()
            self.fail('Should have seen an end of resource exception')
        except EndOfResource:
            pass

    def test_image_selection(self):
       if os.path.exists('imageset.txt'):
           os.remove('imageset.txt')
       with open('imageset.txt', 'w') as fp:
           fp.writelines([filename + os.linesep for filename in os.listdir('tests/images') if
                          not filename.startswith('test_project')])
       if os.path.exists('test_projects'):
           shutil.rmtree('test_projects')
       os.mkdir('test_projects')
       batch_project.loadCustomFunctions()
       batchProject = batch_project.loadJSONGraph('tests/simple_image_selector_plugin.json')
       global_state = {
           'projects': 'test_projects',
           'project': batchProject,
           'picklists_files': {},
           'workdir': '.',
           'count': batch_project.IntObject(20),
           'permutegroupsmanager': PermuteGroupManager()
       }
       batchProject.loadPermuteGroups(global_state)
       batchProject.executeOnce(global_state)

    def test_runwithpermutation(self):
       if os.path.exists('imageset.txt'):
           os.remove('imageset.txt')
       with open('imageset.txt', 'w') as fp:
           fp.writelines([filename + os.linesep for filename in os.listdir('tests/images') if
                          not filename.startswith('test_project')])
       if os.path.exists('test_projects'):
           shutil.rmtree('test_projects')
       os.mkdir('test_projects')
       batch_project.loadCustomFunctions()
       batchProject = batch_project.loadJSONGraph('tests/permutation_batch_process.json')
       global_state = {
           'projects': 'test_projects',
           'project': batchProject,
           'picklists_files': {},
           'count': batch_project.IntObject(20),
           'permutegroupsmanager': PermuteGroupManager()
       }
       batchProject.loadPermuteGroups(global_state)
       for i in range(100):
           batchProject.executeOnce(global_state)
       self.assertTrue(global_state['permutegroupsmanager'].hasNext())

if __name__ == '__main__':
    unittest.main()
