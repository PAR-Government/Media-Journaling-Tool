from maskgen import image_graph
import unittest
import os
import shutil
from maskgen.batch import batch_project
from maskgen.batch.batch_process import processSpecification
from maskgen.batch.permutations import *
from threading import Lock
from maskgen import plugins
from maskgen.tool_set import openImageFile
from tests.test_support import TestSupport
from networkx.readwrite import json_graph


def saveAsPng(source, target):
    openImageFile(source, args={'Bits per Channel': 16}).save(target, format='PNG')


class TestBatchProcess(TestSupport):

    def setUp(self):
        plugins.loadPlugins()

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
                        'image_dir' :self.locateFile('test/images'),
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

    def test_value_shortcut(self):
        self.assertEqual('foo', batch_project.executeParamSpec('test_value_spec', 'foo',
                                                               {}, {}, 'test_node', []))

    def test_list_picker(self):
        manager = PermuteGroupManager()
        global_state = {'iteratorslock': Lock(),
                        'image_dir': self.locateFile('test/images'),
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
        self.addFileToRemove('testimages', preemptive=True)
        shutil.copytree(os.path.dirname(self.locateFile('./images/sample.json')), 'testimages')
        self.assertTrue(processSpecification(self.locateFile('tests/specifications/batch_extension_process.json'), '', 'testimages') == 1)

    def test_run(self):
        self.addFileToRemove('imageset.txt', preemptive=True)
        with open('imageset.txt', 'w') as fp:
            fp.writelines([filename + os.linesep for filename in os.listdir(self.locateFile('tests/images')) if
                           not filename.startswith('test_project')])
        self.addFileToRemove('test_projects', preemptive=True)
        os.mkdir('test_projects')
        batch_project.loadCustomFunctions()
        batchProject = batch_project.loadJSONGraph(self.locateFile('tests/specifications/batch_process.json'))
        global_state = {
            'projects': 'test_projects',
            'project': batchProject,
            'picklists_files': {},
            'workdir': '.',
            'image_dir': self.locateFile('tests/images'),
            'count': batch_project.IntObject(20),
            'permutegroupsmanager': PermuteGroupManager()
        }
        batchProject.loadPermuteGroups(global_state)
        for i in range(2):
            batchProject.executeOnce(global_state)
        try:
            #self.assertFalse(global_state['permutegroupsmanager'].hasNext())
            global_state['permutegroupsmanager'].next()
            self.assertTrue(global_state['permutegroupsmanager'].hasNext())
            global_state['permutegroupsmanager'].next()
            self.fail('Should have seen an end of resource exception')
        except EndOfResource:
            pass

    def test_image_selection(self):
        self.addFileToRemove('imageset.txt', preemptive=True)
        with open('imageset.txt', 'w') as fp:
            fp.writelines([filename + os.linesep for filename in os.listdir(self.locateFile('tests/images')) if
                           not filename.startswith('test_project')])
        if os.path.exists('test_projects'):
            shutil.rmtree('test_projects')
        os.mkdir('test_projects')
        batch_project.loadCustomFunctions()
        batchProject = batch_project.loadJSONGraph(self.locateFile('tests/specifications/simple_image_selector_plugin.json'))
        be = batch_project.BatchExecutor('test_projects',global_variables= {'image_dir' :self.locateFile('tests/images')})
        be.runProjectLocally(batchProject)
        be.finish()

    def test_external_image_selection(self):
        self.addFileToRemove('imageset.txt', preemptive=True)
        with open('imageset.txt', 'w') as fp:
            fp.writelines([filename + os.linesep for filename in os.listdir(self.locateFile('tests/images')) if
                           not filename.startswith('test_project1')])
        if os.path.exists('results'):
            shutil.rmtree('results')
        if os.path.exists('test_projects'):
            shutil.rmtree('test_projects')
        os.mkdir('test_projects')
        os.mkdir('test_projects/hdf5')
        with open('test_projects/hdf5/test_project1.hdf5','w') as fp:
            fp.write('foo')

        be = batch_project.BatchExecutor('test_projects',
                                         global_variables= {'image_dir' :self.locateFile('tests/images'),
                                                            'hdf5dir':'test_projects/hdf5'})
        batch_project.loadCustomFunctions()
        batchProject = batch_project.loadJSONGraph(self.locateFile('tests/specifications/external_image_batch_process.json'))

        self.addFileToRemove('results', preemptive=True)
        self.addFileToRemove('test_projects', preemptive=False)
        os.mkdir('results')
        saveAsPng(self.locateFile('tests/images/test_project1.jpg'), 'results/test_project1.png')
        with open('results/arguments.csv', 'w') as fp:
            fp.write('test_project1.png,no,16')
        be.runProjectLocally(batchProject)
        be.finish()
        self.assertTrue(os.path.exists('test_projects/test_project1/test_project1.hdf5'))


    def test_runwithpermutation(self):
        self.addFileToRemove('imageset.txt', preemptive=True)
        with open('imageset.txt', 'w') as fp:
            fp.writelines([filename + os.linesep for filename in os.listdir(self.locateFile('tests/images')) if
                           not filename.startswith('test_project')])
        if os.path.exists('test_projects'):
            shutil.rmtree('test_projects')
        os.mkdir('test_projects')
        batch_project.loadCustomFunctions()
        batchProject = batch_project.loadJSONGraph(self.locateFile('tests/specifications/permutation_batch_process.json'))
        global_state = {
            'projects': 'test_projects',
            'project': batchProject,
            'picklists_files': {},
            'image_dir': self.locateFile('tests/images'),
            'count': batch_project.IntObject(20),
            'permutegroupsmanager': PermuteGroupManager()
        }
        batchProject.loadPermuteGroups(global_state)
        for i in range(100):
            batchProject.executeOnce(global_state)
        self.assertTrue(global_state['permutegroupsmanager'].hasNext())

    def test_remap(self):
        network = {
            "directed": True,
            "graph": {
                "username": "test",
            },
            "nodes": [
                {
                    "id": "A"
                },
                {
                    "id": "B"
                }
            ],
            "links": [
                {
                    "source": "A",
                    "target": "B"
                }
            ],
            "multigraph": False
        }
        remapped = batch_project.remap_links(network)
        G = json_graph.node_link_graph(remapped, multigraph=False, directed=True)
        self.assertTrue(G.edge['A']['B'] is not None)

if __name__ == '__main__':
    unittest.main()