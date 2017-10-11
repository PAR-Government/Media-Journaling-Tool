from maskgen import graph_rules
import unittest
from maskgen.scenario_model import loadProject
from maskgen.image_graph import ImageGraph
from maskgen import Probe
import numpy as np
import networkx as nx


class ImageGraphB:
    def __init__(self, G):
        """

        :param G:
        @type G: nx.DiGraph
        """
        self.G = G

    def successors(self, node):
        return self.G.successors(node)

    def get_node(self, node):
        return self.G.node[node]

    def get_edge(self, start, end):
        return self.G[start][end] if (self.G.has_edge(start, end)) else None

    def get_nodes(self):
        return self.G.nodes()


class TestToolSet(unittest.TestCase):
    def test_compositeIdAssigner(self):
        G = nx.DiGraph(name="Empty")
        for i in xrange(1, 16):
            G.add_node(str(i), nodetype='base' if i == 1 else ('final' if i in [6, 7, 9, 10,13] else 'intermediate'))
        G.add_edge('1', '2',  op='OutputPng', recordInCompositeMask=True)
        G.add_edge('2', '3',  op='TransformAffine', recordInCompositeMask=False)
        G.add_edge('2', '4',  op='OutputPng', recordInCompositeMask=True)
        G.add_edge('3', '5',  op='OutputPng', recordInCompositeMask=True)
        G.add_edge('5', '6',  op='OutputPng', recordInCompositeMask=True)
        G.add_edge('5', '7',  op='OutputPng', recordInCompositeMask=True)
        G.add_edge('4', '8',  op='TransformResize', recordInCompositeMask=False)
        G.add_edge('8', '9',  op='OutputPng', recordInCompositeMask=True)
        G.add_edge('8', '10', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('1', '11', op='OutputPng', recordInCompositeMask=False)
        G.add_edge('11', '12', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('12', '13', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('5', '14', op='TransformResize', recordInCompositeMask=False)
        G.add_edge('14', '15', op='OutputPng', recordInCompositeMask=False)
        g = ImageGraphB(G)
        probe12branch1 = np.random.randint(0,2,size=(10,10))
        probe12branch2 = np.random.randint(0, 2, size=(10, 10))
        probe12branch3 = np.random.randint(0, 2, size=(12, 12))
        probe24branch2 = np.random.randint(0, 2, size=(10, 10))
        probe35 = np.random.randint(0, 2, size=(10, 10))
        probe35branch3 = np.random.randint(0, 2, size=(12, 12))
        probe56 = np.random.randint(0, 2, size=(10, 10))
        probe57 = np.random.randint(0, 2, size=(10, 10))
        probe89 = np.random.randint(0, 2, size=(10, 10))
        probe810 = np.random.randint(0, 2, size=(10, 10))
        probe1112= np.random.randint(0, 2, size=(11, 11))
        probes = [Probe(('1', '2'), '10', '1', probe12branch2, None, None, None, None, None),
                  Probe(('1', '2'), '9', '1', probe12branch2, None, None, None, None, None),
                  Probe(('1', '2'), '6', '1', probe12branch1, None, None, None, None, None),
                  Probe(('1', '2'), '7', '1', probe12branch1, None, None, None, None, None),
                  Probe(('1', '2'), '15', '1', probe12branch3, None, None, None, None, None),
                  Probe(('2', '4'), '9', '1', probe24branch2, None, None, None, None, None),
                  Probe(('2', '4'), '10', '1', probe24branch2, None, None, None, None, None),
                  Probe(('3', '5'), '6', '1', probe35, None, None, None, None, None),
                  Probe(('3', '5'), '7', '1', probe35, None, None, None, None, None),
                  Probe(('3', '5'), '15', '1', probe35branch3, None, None, None, None, None),
                  Probe(('5', '6'), '6', '1', probe56, None, None, None, None, None),
                  Probe(('5', '7'), '7', '1', probe57, None, None, None, None, None),
                  Probe(('8', '9'), '9', '1', probe89, None, None, None, None, None),
                  Probe(('8', '10'), '10', '1', probe810, None, None, None, None, None),
                  Probe(('11', '12'), '13', '1', probe1112, None, None, None, None, None)
                  ]
        graphCompositeIdAssigner = graph_rules.GraphCompositeIdAssigner(g)
        probes =  graphCompositeIdAssigner.updateProbes(probes,'builder')
        index = {}
        targets = {}
        for probe in probes:
            groupid = probe.composites['builder']['groupid']
            targetid = probe.composites['builder']['bit number']
            index[(probe.edgeId, probe.finalNodeId)] = (groupid, targetid)
            self.assertTrue(targetid > 0)
            if (groupid, targetid) not in targets:
                targets[(groupid, targetid)] = probe.edgeId
            else:
                self.assertEquals(targets[(groupid, targetid)], probe.edgeId)
        self.assertEquals(index[(('1','2'),'10')],index[(('1','2'),'9')])
        self.assertEquals(index[(('2', '4'), '10')], index[(('2', '4'), '9')])
        self.assertNotEquals(index[(('1', '2'), '10')], index[(('1', '2'), '7')])


    def test_aproject(self):
        model = loadProject('images/sample.json')
        leafBaseTuple = model.getTerminalAndBaseNodeTuples()[0]
        result = graph_rules.setFinalNodeProperties(model, leafBaseTuple[0])
        self.assertEqual('yes', result['manmade'])
        self.assertEqual('no', result['face'])
        self.assertEqual('no', result['postprocesscropframes'])
        self.assertEqual('no', result['spatialother'])
        self.assertEqual('no', result['otherenhancements'])
        self.assertEqual('yes', result['color'])
        self.assertEqual('no', result['blurlocal'])
        self.assertEqual('large', result['compositepixelsize'])
        self.assertEqual('yes', result['imagecompression'])


if __name__ == '__main__':
    unittest.main()
