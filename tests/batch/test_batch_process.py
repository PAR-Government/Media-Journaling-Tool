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
from maskgen.support import getValue
from networkx.readwrite import json_graph


def saveAsPng(source, target):
    openImageFile(source, args={'Bits per Channel': 16}).save(target, format='PNG')


class PluginDeferCaller(plugins.PluginCaller):

    def __init__(self,provided_broker):
        provided_broker.register('PluginManager', self)

    def _callPlugin(self, definition, im, source, target, **kwargs):
        if 'Blur' in definition['operation']['name']:
            return  None, None
        return plugins.PluginCaller._callPlugin(self,definition, im, source, target, **kwargs)

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
        self.assertEqual(1, batch_project.executeParamSpec('test_value_spec', {'type':'value','value':'{foo}','function':'numpy.int'},
                                                               {'foo':1}, {}, 'test_node', []))
        self.assertEqual(1, batch_project.executeParamSpec('test_value_spec',
                                                           {'type': 'value', 'value': '{foo@nodex}', 'function': 'numpy.int'},
                                                           {'foo': 2}, {'nodex':{'foo':1}}, 'test_node', []))
        self.assertEqual('2,331.23', batch_project.executeParamSpec('test_value_spec',
                                                           {'type': 'value', 'value': '{foo@nodex:,}'},
                                                           {'foo': 2}, {'nodex': {'foo': 2331.23}}, 'test_node', []))

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

    def general_setup(self):
        self.addFileToRemove('imageset.txt', preemptive=True)
        with open('imageset.txt', 'w') as fp:
            fp.writelines([filename + os.linesep for filename in os.listdir(self.locateFile('tests/images')) if
                           not filename.startswith('test_project')])
        self.addFileToRemove('donorset.txt', preemptive=True)
        with open('donorset.txt', 'w') as fp:
                fp.writelines([filename + os.linesep for filename in os.listdir(self.locateFile('tests/images')) if
                               not filename.startswith('test_project')])
        if os.path.exists('test_projects'):
            shutil.rmtree('test_projects')
        os.mkdir('test_projects')
        batch_project.loadCustomFunctions()

    def test_validation(self):
        self.general_setup()
        manager = plugins.loadPlugins()
        PluginDeferCaller(manager.getBroker())
        batchProject = batch_project.loadJSONGraph(
            self.locateFile('tests/specifications/batch_validation_process.json'))
        be = batch_project.BatchExecutor('test_projects',
                                         global_variables={'image_dir': self.locateFile('tests/images')})
        dir,name= be.runProjectLocally(batchProject)
        be.finish()
        self.assertTrue(dir is None)
        plugins.PluginCaller(manager.getBroker())

    def test_extend(self):
        batch_project.loadCustomFunctions()
        import shutil
        self.addFileToRemove('testimages', preemptive=True)
        shutil.copytree(os.path.dirname(self.locateFile('./images/sample.json')), 'testimages')
        self.assertTrue(processSpecification(self.locateFile('tests/specifications/batch_extension_process.json'), '', 'testimages',skipValidation=True) == 1)

    def test_run(self):
        self.general_setup()
        batchProject = batch_project.loadJSONGraph(self.locateFile('tests/specifications/batch_process.json'))
        global_state = {
            'projects': 'test_projects',
            'project': batchProject,
            'picklists_files': {},
            'workdir': '.',
            'image_dir': self.locateFile('tests/images'),
            'count': batch_project.IntObject(20),
            'permutegroupsmanager': PermuteGroupManager(),
            'donorImages':self.locateFile('tests/images')
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
        self.general_setup()
        batch_project.loadCustomFunctions()
        batchProject = batch_project.loadJSONGraph(self.locateFile('tests/specifications/simple_image_selector_plugin.json'))
        be = batch_project.BatchExecutor('test_projects',skipValidation=True,global_variables= {'image_dir' :self.locateFile('tests/images')})
        dir, name = be.runProjectLocally(batchProject)
        be.finish()
        self.assertTrue(dir is not None)

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
        dir, name = be.runProjectLocally(batchProject)
        be.finish()
        self.assertTrue(dir is not None)
        self.assertTrue(os.path.exists('test_projects/test_project1/test_project1.hdf5'))

    def test_runinheritance(self):
        self.addFileToRemove('imageset.txt', preemptive=True)
        with open('imageset.txt', 'w') as fp:
            fp.writelines([filename + os.linesep for filename in os.listdir(self.locateFile('tests/images')) if
                           not filename.startswith('test_project')])
        if os.path.exists('test_projects'):
            shutil.rmtree('test_projects')
        os.mkdir('test_projects')
        batch_project.loadCustomFunctions()
        batchProject = batch_project.loadJSONGraph(self.locateFile('tests/specifications/inheritance_test.json'))
        global_state = {
            'projects': 'test_projects',
            'project': batchProject,
            'picklists_files': {},
            'image_dir': self.locateFile('tests/images'),
            'count': batch_project.IntObject(1),
            'permutegroupsmanager': PermuteGroupManager()
        }
        batchProject.loadPermuteGroups(global_state)
        for i in range(1):
            batchProject.executeOnce(global_state)


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

    def test_remap2(self):
        network = {
            "directed": True,
            "graph": {
                "username": "test",
            },
            "nodes": [
                {
                    "id": "A",
                    "fooA":"barA"
                },
                {
                    "id": "B",
                    "fooB": "barB"
                },
                {
                    "id": "C",
                    "fooC": "barC"
                },
                {
                    "id": "D",
                    "fooD": "barD",
                    'source':'A'
                },
                {
                    "id": "E",
                    "fooE": "barE"
                }
            ],
            "links": [
                {
                    "source": "A",
                    "target": "B"
                },
                {
                    "source": "A",
                    "target": "D"
                },
                {
                    "source": "B",
                    "target": "C"
                },
                {
                    "source": "C",
                    "target": "D",
                    "split":True
                },
                {
                    "source": "D",
                    "target": "E",
                    "foo":"bar"
                }

            ],
            "multigraph": False
        }
        remapped = batch_project.remap_links(network)
        G = json_graph.node_link_graph(remapped, multigraph=False, directed=True)
        G = batch_project.separate_paths(G)
        for node_id in G.nodes():
            preds = [pred for pred in G.predecessors(node_id) if not getValue(G[pred][node_id], 'donor', False)]
            self.assertTrue(len(preds)<2)
        self.assertEqual(7,len(G.nodes()))



if __name__ == '__main__':
    unittest.main()
