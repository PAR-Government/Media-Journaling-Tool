from maskgen import graph_rules
import unittest
from maskgen.scenario_model import loadProject
from maskgen.image_graph import ImageGraph
from maskgen import Probe
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
        for i in xrange(1, 14):
            G.add_node(str(i), nodetype='base' if i == 1 else ('final' if i in [6, 7, 9, 10,13] else 'intermediate'))
        G.add_edge('1', '2',  op='OutputPng', recordInCompositeMask=True)
        G.add_edge('2', '3',  op='TransformResize', recordInCompositeMask=False)
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
        g = ImageGraphB(G)
        probes = [Probe(('1', '2'), '10', '1', None, None, None, None, None, None),
                  Probe(('1', '2'), '9', '1', None, None, None, None, None, None),
                  Probe(('1', '2'), '6', '1', None, None, None, None, None, None),
                  Probe(('1', '2'), '7', '1', None, None, None, None, None, None),
                  Probe(('2', '4'), '9', '1', None, None, None, None, None, None),
                  Probe(('2', '4'), '10', '1', None, None, None, None, None, None),
                  Probe(('3', '5'), '6', '1', None, None, None, None, None, None),
                  Probe(('3', '5'), '7', '1', None, None, None, None, None, None),
                  Probe(('5', '6'), '6', '1', None, None, None, None, None, None),
                  Probe(('5', '7'), '7', '1', None, None, None, None, None, None),
                  Probe(('8', '9'), '9', '1', None, None, None, None, None, None),
                  Probe(('8', '10'), '10', '1', None, None, None, None, None, None),
                  Probe(('11', '12'), '13', '1', None, None, None, None, None, None)
                  ]
        graphCompositeIdAssigner = graph_rules.GraphCompositeIdAssigner(g, probes)
        targets = {}
        for probe in graphCompositeIdAssigner.probes:
            self.assertTrue(probe.targetid > 0)
            self.assertTrue(probe.edgeId != ('11','12') or probe.groupid==0)
            self.assertTrue(probe.edgeId != ('1', '2') or probe.groupid in [1,2])
            if (probe.groupid,probe.targetid) not in targets:
                targets[(probe.groupid,probe.targetid)] = probe.edgeId
            else:
                self.assertTrue(targets[(probe.groupid,probe.targetid)] == probe.edgeId)


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
        self.assertEqual('small', result['compositepixelsize'])
        self.assertEqual('yes', result['imagecompression'])


if __name__ == '__main__':
    unittest.main()
