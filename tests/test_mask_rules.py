from maskgen.mask_rules import *
import unittest
from maskgen.image_graph import ImageGraph
import numpy as np
import networkx as nx
from tests.test_support import TestSupport

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



class TestMaskRules(TestSupport):

    def test_recapture_transform(self):
        edge = { u'maskname': u'Rotate_mask.png',
                  u'inputmaskname': None,
                  u'shape change': u'(0, 0)',
                 'empty mask': 'no',
                 u'arguments': {u'Position Mapping': '(86, 0, 2860, 3973):(0, 0, 7968, 5313):90'},
                 u'transform matrix': {u'c': 3,
                                       u'r': 3,
                                       u'r0': [0.8266647515769302, 0.07178941510501777, 159.50098419871705],
                                       u'r1': [-0.06021837537671073, 0.9344977768387763, 137.85479973696164],
                                       u'r2': [-3.946051215265123e-05, 1.8621034727368588e-05, 1.0]},
                 u'op': u'Recapture'}
        buildState = BuildState(edge,
                                self.locateFile('images/PostRotate.png'),
                                self.locateFile('images/PostRotate.png'), #does not matter
                                openImageFile(self.locateFile('images/Recapture_mask.png'),isMask=True).image_array,
                                (3984, 2988),
                                (5320, 7968),
                                directory='.',
                                compositeMask=openImageFile(self.locateFile('images/Rotate_mask.png'), isMask=True).image_array,
                                pred_edges=None,
                                graph=None)
        result = recapture_transform(buildState)
        self.assertEquals((5320, 7968), result.shape)

        buildState = BuildState(edge,
                                self.locateFile('images/PostRotate.png'),
                                self.locateFile('images/PostRotate.png'), #does not matter
                                openImageFile(self.locateFile('images/Recapture_mask.png'),isMask=True).image_array,
                                (3984, 2988),
                                (5320, 7968),
                                directory='.',
                                donorMask=result,
                                pred_edges=None,
                                graph=None)
        result= recapture_transform(buildState)
        self.assertEquals((3984, 2988), result.shape)

        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {},
                u'transform matrix': {u'c': 3,
                                      u'r': 3,
                                      u'r0': [0.8266647515769302, 0.07178941510501777, 159.50098419871705],
                                      u'r1': [-0.06021837537671073, 0.9344977768387763, 137.85479973696164],
                                      u'r2': [-3.946051215265123e-05, 1.8621034727368588e-05, 1.0]},
                u'op': u'Recapture'}
        buildState = BuildState(edge,
                                self.locateFile('images/PostRotate.png'),
                                self.locateFile('images/PostRotate.png'),  # does not matter
                                openImageFile(self.locateFile('images/Recapture_mask.png'), isMask=True).image_array,
                                (3984, 2988),
                                (5320, 7968),
                                directory='.',
                                compositeMask=openImageFile(self.locateFile('images/Rotate_mask.png'),
                                                            isMask=True).image_array,
                                pred_edges=None,
                                graph=None)
        result = recapture_transform(buildState)
        self.assertEquals((5320, 7968),result.shape)

        buildState = BuildState(edge,
                                self.locateFile('images/PostRotate.png'),
                                self.locateFile('images/PostRotate.png'),  # does not matter
                                openImageFile(self.locateFile('images/Recapture_mask.png'), isMask=True).image_array,
                                (3984, 2988),
                                (5320, 7968),
                                directory='.',
                                donorMask=result,
                                pred_edges=None,
                                graph=None)
        result =recapture_transform(buildState)
        self.assertEquals((3984, 2988), result.shape)


    def test_rotate_transform(self):
        edge = { u'maskname': u'Rotate_mask.png',
                  u'inputmaskname': None,
                  u'shape change': u'(0, 0)',
                 'empty mask': 'no',
                 u'arguments': {u'rotation': 358},
                 u'transform matrix': {u'c': 3,
                                       u'r': 3,
                                       u'r0': [0.8266647515769302, 0.07178941510501777, 159.50098419871705],
                                       u'r1': [-0.06021837537671073, 0.9344977768387763, 137.85479973696164],
                                       u'r2': [-3.946051215265123e-05, 1.8621034727368588e-05, 1.0]},
                 u'op': u'TransformRotate'}
        buildState = BuildState(edge,
                                self.locateFile('images/PreRotate.png'),
                                self.locateFile('images/PostRotate.png'),
                                openImageFile(self.locateFile('images/Rotate_mask.png'),isMask=True).image_array,
                                (3984, 2988),
                                (3984, 2988),
                                directory='.',
                                compositeMask=openImageFile(self.locateFile('images/Rotate_mask.png'), isMask=True).image_array,
                                pred_edges=None,
                                graph=None)
        result = rotate_transform(buildState)
        self.assertEqual((3984, 2988), result.shape)

        buildState = BuildState(edge,
                                self.locateFile('images/PreRotate.png'),
                                self.locateFile('images/PostRotate.png'),
                                openImageFile(self.locateFile('images/Rotate_mask.png'),isMask=True).image_array,
                                (3984, 2988),
                                (3984, 2988),
                                directory='.',
                                donorMask=result,
                                pred_edges=None,
                                graph=None)
        result = rotate_transform(buildState)
        self.assertEqual((3984, 2988),result.shape)

        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(-996, 996)',
                'empty mask': 'no',
                u'arguments': {u'rotation': 90},
                u'op': u'TransformRotate'}
        buildState = BuildState(edge,
                                self.locateFile('images/PreRotate.png'),
                                self.locateFile('images/PostRotate.png'),
                                openImageFile(self.locateFile('images/Rotate_mask.png'), isMask=True).image_array,
                                (3984, 2988),
                                (2988, 3984),
                                directory='.',
                                compositeMask=openImageFile(self.locateFile('images/Rotate_mask.png'),
                                                            isMask=True).image_array,
                                pred_edges=None,
                                graph=None)
        result = rotate_transform(buildState)
        self.assertEqual((2988,3984), result.shape)

        buildState = BuildState(edge,
                                self.locateFile('images/PreRotate.png'),
                                self.locateFile('images/PostRotate.png'),
                                openImageFile(self.locateFile('images/Rotate_mask.png'), isMask=True).image_array,
                                (3984, 2988),
                                (3984, 2988),
                                directory='.',
                                donorMask=result,
                                pred_edges=None,
                                graph=None)
        result = rotate_transform(buildState)
        self.assertEqual((3984, 2988), result.shape)

    def test_resize_transform(self):
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(-100, -100)',
                'empty mask': 'no',
                u'arguments': {'interpolation':'other'},
                u'op': u'TransformResize'}
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3),dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3),dtype=np.uint8),
                                np.zeros((3984, 2988),dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=np.ones((3984, 2988),dtype=np.uint8),
                                pred_edges=None,
                                graph=None)
        result = resize_transform(buildState)
        self.assertEqual((3884, 2888), result.shape)
        self.assertEqual(1, result[11, 11])

        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(-100, -100)',
                'empty mask': 'no',
                u'arguments': {'location':'10,10',
                               'interpolation':'none',
                               u'transform matrix': {u'c': 3,
                                                     u'r': 3,
                                                     u'r0': [1, 0,
                                                             2],
                                                     u'r1': [0, 1, 12],
                                                     u'r2': [0, 0, 1.0]}
                               },
                u'op': u'TransformResize'}
        mask = np.zeros((3984, 2988), dtype=np.uint8)
        mask[200:300,200:300]=1
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                mask,
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=mask,
                                pred_edges=None,
                                graph=None)
        result = resize_transform(buildState)
        self.assertEqual((3884, 2888), result.shape)
        self.assertEqual(0, result[201,201])
        self.assertEqual(1, result[212, 212])
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8)*255,
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                donorMask=result*255,
                                pred_edges=None,
                                graph=None)
        result = resize_transform(buildState)
        self.assertEqual((3984, 2988), result.shape)
        ImageWrapper(result).save('foo.png')
        self.assertEqual(255, result[205, 206])



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
        probes = [Probe(('1', '2'), '10', '1', None,targetMaskImage=probe12branch2),
                  Probe(('1', '2'), '9', '1', None,targetMaskImage=probe12branch2),
                  Probe(('1', '2'), '6', '1',None,targetMaskImage=probe12branch1),
                  Probe(('1', '2'), '7', '1',None,targetMaskImage= probe12branch1),
                  Probe(('1', '2'), '15', '1',None,targetMaskImage=probe12branch3),
                  Probe(('2', '4'), '9', '1',None,targetMaskImage=probe24branch2),
                  Probe(('2', '4'), '10', '1', None,targetMaskImage=probe24branch2),
                  Probe(('3', '5'), '6', '1', None,targetMaskImage=probe35),
                  Probe(('3', '5'), '7', '1', None,targetMaskImage=probe35),
                  Probe(('3', '5'), '15', '1', None,targetMaskImage=probe35branch3),
                  Probe(('5', '6'), '6', '1',None,targetMaskImage= probe56),
                  Probe(('5', '7'), '7', '1',None,targetMaskImage= probe57),
                  Probe(('8', '9'), '9', '1', None,targetMaskImage=probe89),
                  Probe(('8', '10'), '10', '1', None,targetMaskImage=probe810),
                  Probe(('11', '12'), '13', '1', None,targetMaskImage=probe1112)
                  ]
        graphCompositeIdAssigner = GraphCompositeIdAssigner(g)
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