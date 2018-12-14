import networkx as nx
import numpy as np
from maskgen.mask_rules import *
from mock import *
from test_support import TestSupport


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

    def test_add_audio(self):
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                u'empty mask': 'no',
                u'arguments': {'voice': 'no',
                               'add type': 'replace',
                               'filter type': 'Other',
                               'synchronization': 'none',
                               'Start Time': '00:00:00',
                               'Stream': 'all',
                               'Direct from PC': 'no'
                               },
                u'op': u'AddAudioSample'}
        mask = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=4,
            endframe=176400,
            frames=176399,
            rate=44100,
            error=0,
            type='audio')
        cm = CompositeImage(source='a', target='b', media_type='audio', mask=[mask])
        graph = Mock()
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': .2267,
                'startframe': 10000,
                'endtime': .4535,
                'endframe': 20000,
                'frames': 10000,
                'type': 'audio',
                'rate': 44100
            })]
            result = add_audio(mock_composite)
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(9999,
                             video_tools.get_end_frame_from_segment(result.videomasks[0]))
            self.assertEqual(20001,
                             video_tools.get_start_frame_from_segment(result.videomasks[1]))



    def test_copy_add_audio(self):
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                u'empty mask': 'no',
                u'arguments': {'voice': 'no',
                               'add type': 'replace',
                               'filter type': 'Other',
                               'synchronization': 'none',
                               'Copy Start Time': '00:00:00',
                               'Copy End Time': '00:01:00',
                               'Insertion Time': '00:03:00',
                               'Stream': 'all',
                               'Direct from PC': 'no'
                               },
                u'op': u'AudioCopyAdd'}
        mask = video_tools.create_segment(
            starttime=3000,
            startframe=132300,
            endtime=4000,
            endframe=176400,
            frames=44100,
            rate=44100,
            error=0,
            type='audio')
        cm = CompositeImage(source='a', target='b', media_type='audio', mask=[mask])
        graph = Mock()
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 3500,
                'startframe': 154350,
                'endtime': 4500,
                'endframe': 198450,
                'frames': 44100,
                'type': 'audio',
                'rate': 44100
            })]
            result = copy_add_audio(mock_composite)
            self.assertEqual(1, len(result.videomasks))
            self.assertEqual(154349,
                             video_tools.get_end_frame_from_segment(result.videomasks[0]))
            self.assertEqual(132300,
                             video_tools.get_start_frame_from_segment(result.videomasks[0]))

        edge['arguments']['add type'] = 'insert'
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 3500,
                'startframe': 154350,
                'endtime': 4500,
                'endframe': 198450,
                'frames': 44101,
                'type': 'audio',
                'rate': 44100
            })]
            result = copy_add_audio(mock_composite)
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(154349,
                             video_tools.get_end_frame_from_segment(result.videomasks[0]))
            self.assertEqual(198451,
                             video_tools.get_start_frame_from_segment(result.videomasks[1]))
            self.assertEqual(22050,
                             video_tools.get_frames_from_segment(result.videomasks[0]))
            self.assertEqual(22051,
                             video_tools.get_frames_from_segment(result.videomasks[1]))

    def test_replace_audio(self):
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'voice': 'no',
                               'filter type': 'Other',
                               'Stream': 'all',
                               },
                u'op': u'ReplaceAudioSample'}
        mask = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=4,
            endframe=176400,
            frames=176399,
            rate=44100,
            error=0,
            type='audio')
        cm = CompositeImage(source='a', target='b', media_type='audio', mask=[mask])
        graph = Mock()
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 0,
                'startframe': 1,
                'endtime': 4,
                'endframe': 176400,
                'frames': 176399,
                'type': 'audio',
                'rate': 44800
            })]
            result = replace_audio(mock_composite)
            self.assertEqual(0, len(result.videomasks))

    def test_output(self):
        edge = {u'maskname': u'output_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(-100, -100)',
                'empty mask': 'no',
                u'op': u'OutputMOV'}
        mask = video_tools.create_segment(
            starttime=1400,
            startframe=15,
            endtime=2400,
            endframe=25,
            frames=11,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()
        graph.get_node = Mock(return_value={'shape': '(3984, 2988)'})
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3784, 2788, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3784, 2788),
                                directory='.',
                                donorMask=None,
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.shapeChange = buildState.shapeChange
            mock_composite.getVideoMetaExtractor = buildState.getVideoMetaExtractor
            mock_composite.warpMask.return_value = CompositeImage('a', 'b', 'video', [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })])
            mock_composite.compositeMask = cm
            mock_composite.isComposite = True
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = output_video_change(mock_composite)
            self.assertEqual(1, len(result.videomasks))
            self.assertEqual(15, video_tools.get_start_frame_from_segment(result.videomasks[0]))
            self.assertEqual(25, result.videomasks[0]['endframe'])
            self.assertEqual(11, result.videomasks[0]['frames'])
            self.assertEqual(1400, result.videomasks[0]['starttime'])
            self.assertEqual(2400.0, result.videomasks[0]['endtime'])

    def test_crop_resize_transform(self):
        edge = {u'maskname': u'crop_resize_mask.png',
                u'inputmaskname': None,
                u'location': u'(50, 50)',
                'empty mask': 'no',
                u'arguments': {'crop width': 2500, 'crop height': 3500},
                u'op': u'TransformCropResize'}
        img = np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8)
        img_crop = img[10:3500, 10:2500, :]
        img_crop_resize = cv2.resize(img_crop, (img.shape[1], img.shape[0]))
        composite_mask = np.zeros((3984, 2988), dtype=np.uint8)
        composite_mask[0:100, 0:100] = 1

        buildState = BuildState(edge,
                                img,
                                img_crop_resize,
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3984, 2988),
                                directory='.',
                                compositeMask=CompositeImage('a', 'b', 'image', composite_mask),
                                pred_edges=None,
                                graph=None)
        result = crop_resize_transform(buildState)
        self.assertEqual((3984, 2988), result.mask.shape)
        self.assertEqual(1, result.mask[0, 0])
        self.assertEqual(1, result.mask[49, 49])
        self.assertEqual(0, result.mask[61, 61])

        buildState = BuildState(edge,
                                img,
                                img_crop_resize,
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                donorMask=CompositeImage('a', 'b', 'image', composite_mask),
                                pred_edges=None,
                                graph=None)
        result = crop_resize_transform(buildState)
        self.assertEqual(0, result.mask[0, 0])
        self.assertEqual(0, result.mask[10, 10])
        self.assertEqual(1, result.mask[51, 51])

    def test_recapture_transform(self):
        edge = {u'maskname': u'Rotate_mask.png',
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
                                self.locateFile('images/PostRotate.png'),  # does not matter
                                openImageFile(self.locateFile('images/Recapture_mask.png'), isMask=True).image_array,
                                (3984, 2988),
                                (5320, 7968),
                                directory='.',
                                compositeMask=CompositeImage('a', 'b', 'image',
                                                             openImageFile(self.locateFile('images/Rotate_mask.png'),
                                                                           isMask=True).image_array),
                                pred_edges=None,
                                graph=None)
        result = recapture_transform(buildState)
        self.assertEquals((5320, 7968), result.mask.shape)

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
        result = recapture_transform(buildState)
        self.assertEquals((3984, 2988), result.mask.shape)

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
                                compositeMask=CompositeImage('a', 'b', 'image',
                                                             openImageFile(self.locateFile('images/Rotate_mask.png'),
                                                                           isMask=True).image_array),
                                pred_edges=None,
                                graph=None)
        result = recapture_transform(buildState)
        self.assertEquals((5320, 7968), result.mask.shape)

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
        result = recapture_transform(buildState)
        self.assertEquals((3984, 2988), result.mask.shape)

    def test_rotate_transform(self):
        edge = {u'maskname': u'Rotate_mask.png',
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
                                openImageFile(self.locateFile('images/Rotate_mask.png'), isMask=True).image_array,
                                (3984, 2988),
                                (3984, 2988),
                                directory='.',
                                compositeMask=CompositeImage('a', 'b', 'image',
                                                             openImageFile(self.locateFile('images/Rotate_mask.png'),
                                                                           isMask=True).image_array),
                                pred_edges=None,
                                graph=None)
        result = rotate_transform(buildState)
        self.assertEqual((3984, 2988), result.mask.shape)

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
        self.assertEqual((3984, 2988), result.mask.shape)

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
                                compositeMask=CompositeImage('a', 'b', 'image',
                                                             openImageFile(self.locateFile('images/Rotate_mask.png'),
                                                                           isMask=True).image_array),
                                pred_edges=None,
                                graph=None)
        result = rotate_transform(buildState)
        self.assertEqual((2988, 3984), result.mask.shape)

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
        self.assertEqual((3984, 2988), result.mask.shape)

    def test_resize_transform(self):
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(-100, -100)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other'},
                u'op': u'TransformResize'}
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=CompositeImage('a', 'b', 'image', np.ones((3984, 2988), dtype=np.uint8)),
                                pred_edges=None,
                                graph=None)
        result = resize_transform(buildState)
        self.assertEqual((3884, 2888), result.mask.shape)
        self.assertEqual(1, result.mask[11, 11])

        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(-100, -100)',
                'empty mask': 'no',
                u'arguments': {'location': '10,10',
                               'interpolation': 'none',
                               u'transform matrix': {u'c': 3,
                                                     u'r': 3,
                                                     u'r0': [1, 0,
                                                             2],
                                                     u'r1': [0, 1, 12],
                                                     u'r2': [0, 0, 1.0]}
                               },
                u'op': u'TransformResize'}
        mask = np.zeros((3984, 2988), dtype=np.uint8)
        mask[200:300, 200:300] = 1
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                mask,
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=CompositeImage('a', 'b', 'image', mask),
                                pred_edges=None,
                                graph=None)
        result = resize_transform(buildState).mask
        self.assertEqual((3884, 2888), result.shape)
        self.assertEqual(0, result[201, 201])
        self.assertEqual(1, result[212, 212])
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8) * 255,
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                donorMask=CompositeImage('a', 'b', 'image', result * 255),
                                pred_edges=None,
                                graph=None)
        result = resize_transform(buildState).mask
        self.assertEqual((3984, 2988), result.shape)
        ImageWrapper(result).save('foo.png')
        self.assertEqual(255, result[205, 206])

    def test_cas_transform(self):
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                'empty mask': 'no',
                u'arguments': {
                    u'transform matrix': {u'c': 3,
                                          u'r': 3,
                                          u'r0': [0.7, -0.7, 50],
                                          u'r1': [0.7, 0.7, 50],
                                          u'r2': [0, 0, 1.0]}
                },
                u'op': u'TransformContentAwareScale'}
        mask = np.zeros((3984, 2988), dtype=np.uint8)
        cm = np.zeros((3984, 2988), dtype=np.uint8)
        cm[200:300, 200:300] = 1
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                mask,
                                (3984, 2988),
                                (3984, 2988),
                                directory='.',
                                compositeMask=CompositeImage('a', 'b', 'image', cm),
                                pred_edges=None,
                                graph=None)
        result = seam_transform(buildState).mask
        self.assertEqual((3984, 2988), result.shape)
        self.assertEqual(0, result[201, 201])
        self.assertEqual(1, result[330, 50])
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8) * 255,
                                (3984, 2988),
                                (3984, 2988),
                                directory='.',
                                donorMask=CompositeImage('a', 'b', 'image', result * 255),
                                pred_edges=None,
                                graph=None)
        result = resize_transform(buildState).mask
        self.assertEqual((3984, 2988), result.shape)
        self.assertEqual(255, result[201, 201])
        self.assertEqual(0, result[330, 50])

    def test_crop_transform(self):
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(-100, -100)',
                u'location': '50,50',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other'},
                u'op': u'TransformResize'}
        cm = np.zeros((3984, 2988), dtype=np.uint8)
        cm[25:75, 25:75] = 1
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=CompositeImage('a', 'b', 'image', cm),
                                pred_edges=None,
                                graph=None)
        result = crop_transform(buildState).mask
        self.assertEqual((3884, 2888), result.shape)
        self.assertEqual(1, result[0, 0])
        self.assertEqual(0, result[26, 26])

        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                donorMask=CompositeImage('a', 'b', 'image', result),
                                pred_edges=None,
                                graph=None)
        result = crop_transform(buildState).mask
        self.assertEqual((3984, 2988), result.shape)
        self.assertEqual(0, result[0, 0])
        self.assertEqual(0, result[26, 26])
        self.assertEqual(1, result[51, 51])

    def test_select_crop_transform(self):
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'Start Time': 15,
                               'End Time': 25},
                u'op': u'SelectCropFramrs'}
        mask = video_tools.create_segment(
            starttime=0,
            startframe=1,
            endtime=2900,
            endframe=30,
            frames=30,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = select_crop_frames(mock_composite)
            self.assertEqual(1, len(result.videomasks))
            self.assertEqual(1, result.videomasks[0]['startframe'])
            self.assertEqual(11, result.videomasks[0]['endframe'])
            self.assertEqual(11, result.videomasks[0]['frames'])
            self.assertEqual(0.0, result.videomasks[0]['starttime'])
            self.assertEqual(1000.0, result.videomasks[0]['endtime'])

        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                donorMask=cm,
                                compositeMask=None,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.isComposite = False
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = select_crop_frames(mock_donor)
            self.assertEqual(1, len(result.videomasks))
            self.assertEqual(15, result.videomasks[0]['startframe'])
            self.assertEqual(44, result.videomasks[0]['endframe'])
            self.assertEqual(30, result.videomasks[0]['frames'])
            self.assertEqual(1400, result.videomasks[0]['starttime'])
            self.assertEqual(4300.0, result.videomasks[0]['endtime'])

    def test_copy_paste_frames_insert(self):
        # copy into same spot
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'Dest Paste Time': 15,
                               'add type': 'insert',
                               'Number of Frames': 11,
                               'Start Time': 15,
                               'End Time': 25},
                u'op': u'CopyPaste'}
        mask = video_tools.create_segment(
            starttime=1400,
            startframe=15,
            endtime=2400,
            endframe=25,
            frames=11,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_composite)
            self.assertEqual(1, len(result.videomasks))
            self.assertEqual(26, result.videomasks[0]['startframe'])
            self.assertEqual(36, result.videomasks[0]['endframe'])
            self.assertEqual(11, result.videomasks[0]['frames'])
            self.assertEqual(2500, result.videomasks[0]['starttime'])
            self.assertEqual(3500.0, result.videomasks[0]['endtime'])

        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.isComposite = False
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_donor)
            self.assertEqual(0, len(result.videomasks))

        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'Dest Paste Time': 100,
                               'add type': 'insert',
                               'Number of Frames': 11,
                               'Start Time': 15,
                               'End Time': 25},
                u'op': u'CopyPaste'}
        mask = video_tools.create_segment(
            starttime=9000,
            startframe=91,
            endtime=15000,
            endframe=151,
            frames=61,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        # more complex, insert
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_composite)
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(91, result.videomasks[0]['startframe'])
            self.assertEqual(99, result.videomasks[0]['endframe'])
            self.assertEqual(9, result.videomasks[0]['frames'])
            self.assertEqual(9000, result.videomasks[0]['starttime'])
            self.assertEqual(9800.0, result.videomasks[0]['endtime'])
            self.assertEqual(115, result.videomasks[1]['startframe'])
            self.assertEqual(166, result.videomasks[1]['endframe'])
            self.assertEqual(52, result.videomasks[1]['frames'])
            self.assertEqual(11400, result.videomasks[1]['starttime'])
            self.assertEqual(16500.0, result.videomasks[1]['endtime'])

        # more complex, drop
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.isComposite = False
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_donor)
            # two because one was moved down...could combine them
            # but it matters little for our purposes.
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(91, result.videomasks[0]['startframe'])
            self.assertEqual(99, result.videomasks[0]['endframe'])
            self.assertEqual(9, result.videomasks[0]['frames'])
            self.assertEqual(9000, result.videomasks[0]['starttime'])
            self.assertEqual(9800.0, result.videomasks[0]['endtime'])
            self.assertEqual(100, result.videomasks[1]['startframe'])
            self.assertEqual(136, result.videomasks[1]['endframe'])
            self.assertEqual(37, result.videomasks[1]['frames'])
            self.assertEqual(9900, result.videomasks[1]['starttime'])
            self.assertEqual(13500.0, result.videomasks[1]['endtime'])

    def test_copy_paste_frames_replace(self):
        # copy into same spot
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'Dest Paste Time': 15,
                               'add type': 'replace',
                               'Number of Frames': 11,
                               'Select Start Time': 15},
                u'op': u'CopyPaste'}
        mask = video_tools.create_segment(
            starttime=1400,
            startframe=15,
            endtime=2400,
            endframe=25,
            frames=31,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_composite)
            self.assertEqual(0, len(result.videomasks))

        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.isComposite = False
            mock_donor.arguments.return_value = edge['arguments']
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_donor)
            self.assertEqual(1, len(result.videomasks))
            self.assertEqual(
                {'endframe': 25, 'rate': 10, 'starttime': 1400, 'frames': 11, 'startframe': 15, 'endtime': 2400,
                 'type': 'video'},
                result.videomasks[0])

        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'Dest Paste Time': 100,
                               'add type': 'insert',
                               'Number of Frames': 11,
                               'Select Start Time': 15},
                u'op': u'CopyPaste'}
        mask = video_tools.create_segment(
            starttime=9000,
            startframe=91,
            endtime=15000,
            endframe=151,
            frames=61,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        # more complex, insert
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_composite)
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(91, result.videomasks[0]['startframe'])
            self.assertEqual(99, result.videomasks[0]['endframe'])
            self.assertEqual(9, result.videomasks[0]['frames'])
            self.assertEqual(9000, result.videomasks[0]['starttime'])
            self.assertEqual(9800.0, result.videomasks[0]['endtime'])
            self.assertEqual(115, result.videomasks[1]['startframe'])
            self.assertEqual(166, result.videomasks[1]['endframe'])
            self.assertEqual(52, result.videomasks[1]['frames'])
            self.assertEqual(11400, result.videomasks[1]['starttime'])
            self.assertEqual(16500.0, result.videomasks[1]['endtime'])

        # more complex, drop
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.arguments.return_value = edge['arguments']
            mock_donor.isComposite = False
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_donor)
            # two because one was moved down...could combine them
            # but it matters little for our purposes.
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(91, result.videomasks[0]['startframe'])
            self.assertEqual(99, result.videomasks[0]['endframe'])
            self.assertEqual(9, result.videomasks[0]['frames'])
            self.assertEqual(9000, result.videomasks[0]['starttime'])
            self.assertEqual(9800.0, result.videomasks[0]['endtime'])
            self.assertEqual(100, result.videomasks[1]['startframe'])
            self.assertEqual(136, result.videomasks[1]['endframe'])
            self.assertEqual(37, result.videomasks[1]['frames'])
            self.assertEqual(9900, result.videomasks[1]['starttime'])
            self.assertEqual(13500.0, result.videomasks[1]['endtime'])

        # REPLACE
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'Dest Paste Time': 100,
                               'add type': 'replace',
                               'Number of Frames': 11,
                               'Select Start Time': 15},
                u'op': u'CopyPaste'}
        mask = video_tools.create_segment(
            starttime=9000,
            startframe=91,
            endtime=15000,
            endframe=151,
            frames=61,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        # more complex, insert
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_composite)
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual([{'endframe': 99, 'rate': 10, 'starttime': 9000, 'error': 0, 'frames': 9, 'startframe': 91,
                               'endtime': 9800.0, 'type': 'video'},
                              {'endframe': 151, 'rate': 10, 'starttime': 11400, 'error': 0, 'frames': 37,
                               'startframe': 115,
                               'endtime': 15000, 'type': 'video'}],
                             result.videomasks
                             )

        # more complex, drop
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.arguments.return_value = edge['arguments']
            mock_donor.isComposite = False
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_donor)
            # two because one was moved down...could combine them
            # but it matters little for our purposes.
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual([{'endframe': 25, 'rate': 10, 'starttime': 1400, 'frames': 11, 'startframe': 15,
                               'endtime': 2400, 'type': 'video'},
                              {'endframe': 151, 'rate': 10, 'starttime': 9000, 'error': 0, 'frames': 61,
                               'startframe': 91, 'endtime': 15000, 'type': 'video'}],
                             result.videomasks)

    def test_paste_add_frames(self):
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'add type': 'insert',
                               'Number of Frames': 11,
                               'Start Time': 15,
                               'End Time': 25},
                u'op': u'PasteAddFrames'}
        mask = video_tools.create_segment(
            starttime=1400,
            startframe=15,
            endtime=2400,
            endframe=25,
            frames=11,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = paste_add_frames(mock_composite)
            self.assertEqual(1, len(result.videomasks))
            self.assertEqual(26, result.videomasks[0]['startframe'])
            self.assertEqual(36, result.videomasks[0]['endframe'])
            self.assertEqual(11, result.videomasks[0]['frames'])
            self.assertEqual(2500, result.videomasks[0]['starttime'])
            self.assertEqual(3500.0, result.videomasks[0]['endtime'])

        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.arguments.return_value = edge['arguments']
            mock_donor.isComposite = False
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = paste_add_frames(mock_donor)
            self.assertEqual(0, len(result.videomasks))

        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'add type': 'insert',
                               'Number of Frames': 91,
                               'Start Time': 151,
                               'End Time': 61},
                u'op': u'CopyPaste'}
        mask = video_tools.create_segment(
            starttime=9000,
            startframe=91,
            endtime=15000,
            endframe=151,
            frames=61,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        # more complex, insert
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = paste_add_frames(mock_composite)
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(91, result.videomasks[0]['startframe'])
            self.assertEqual(99, result.videomasks[0]['endframe'])
            self.assertEqual(9, result.videomasks[0]['frames'])
            self.assertEqual(9000, result.videomasks[0]['starttime'])
            self.assertEqual(9800.0, result.videomasks[0]['endtime'])
            self.assertEqual(115, result.videomasks[1]['startframe'])
            self.assertEqual(166, result.videomasks[1]['endframe'])
            self.assertEqual(52, result.videomasks[1]['frames'])
            self.assertEqual(11400, result.videomasks[1]['starttime'])
            self.assertEqual(16500.0, result.videomasks[1]['endtime'])

        # more complex, drop
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.isComposite = False
            mock_donor.arguments.return_value = edge['arguments']
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = paste_add_frames(mock_donor)
            # two because one was moved down...could combine them
            # but it matters little for our purposes.
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(91, result.videomasks[0]['startframe'])
            self.assertEqual(99, result.videomasks[0]['endframe'])
            self.assertEqual(9, result.videomasks[0]['frames'])
            self.assertEqual(9000, result.videomasks[0]['starttime'])
            self.assertEqual(9800.0, result.videomasks[0]['endtime'])
            self.assertEqual(100, result.videomasks[1]['startframe'])
            self.assertEqual(136, result.videomasks[1]['endframe'])
            self.assertEqual(37, result.videomasks[1]['frames'])
            self.assertEqual(9900, result.videomasks[1]['starttime'])
            self.assertEqual(13500.0, result.videomasks[1]['endtime'])

    def test_copy_paste_frames_replace(self):
        # copy into same spot
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'Dest Paste Time': 15,
                               'add type': 'replace',
                               'Number of Frames': 11,
                               'Select Start Time': 15},
                u'op': u'CopyPaste'}
        mask = video_tools.create_segment(
            starttime=1400,
            startframe=15,
            endtime=2400,
            endframe=25,
            frames=31,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_composite)
            self.assertEqual(0, len(result.videomasks))

        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.isComposite = False
            mock_donor.arguments.return_value = edge['arguments']
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_donor)
            self.assertEqual(1, len(result.videomasks))
            self.assertEqual(
                {'endframe': 25, 'rate': 10, 'starttime': 1400, 'frames': 11, 'startframe': 15, 'endtime': 2400,
                 'type': 'video', 'error':0},
                result.videomasks[0])

        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'Dest Paste Time': 100,
                               'add type': 'insert',
                               'Number of Frames': 11,
                               'Select Start Time': 15},
                u'op': u'CopyPaste'}
        mask = video_tools.create_segment(
            starttime=9000,
            startframe=91,
            endtime=15000,
            endframe=151,
            frames=61,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        # more complex, insert
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_composite)
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(91, result.videomasks[0]['startframe'])
            self.assertEqual(99, result.videomasks[0]['endframe'])
            self.assertEqual(9, result.videomasks[0]['frames'])
            self.assertEqual(9000, result.videomasks[0]['starttime'])
            self.assertEqual(9800.0, result.videomasks[0]['endtime'])
            self.assertEqual(115, result.videomasks[1]['startframe'])
            self.assertEqual(166, result.videomasks[1]['endframe'])
            self.assertEqual(52, result.videomasks[1]['frames'])
            self.assertEqual(11400, result.videomasks[1]['starttime'])
            self.assertEqual(16500.0, result.videomasks[1]['endtime'])

        # more complex, drop
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.arguments.return_value = edge['arguments']
            mock_donor.isComposite = False
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_donor)
            # two because one was moved down...could combine them
            # but it matters little for our purposes.
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual(91, result.videomasks[0]['startframe'])
            self.assertEqual(99, result.videomasks[0]['endframe'])
            self.assertEqual(9, result.videomasks[0]['frames'])
            self.assertEqual(9000, result.videomasks[0]['starttime'])
            self.assertEqual(9800.0, result.videomasks[0]['endtime'])
            self.assertEqual(100, result.videomasks[1]['startframe'])
            self.assertEqual(136, result.videomasks[1]['endframe'])
            self.assertEqual(37, result.videomasks[1]['frames'])
            self.assertEqual(9900, result.videomasks[1]['starttime'])
            self.assertEqual(13500.0, result.videomasks[1]['endtime'])

        # REPLACE
        edge = {u'maskname': u'Rotate_mask.png',
                u'inputmaskname': None,
                u'shape change': u'(0, 0)',
                'empty mask': 'no',
                u'arguments': {'interpolation': 'other',
                               'Dest Paste Time': 100,
                               'add type': 'replace',
                               'Number of Frames': 11,
                               'Select Start Time': 15},
                u'op': u'CopyPaste'}
        mask = video_tools.create_segment(
            starttime=9000,
            startframe=91,
            endtime=15000,
            endframe=151,
            frames=61,
            rate=10,
            error=0,
            type='video')
        cm = CompositeImage('a', 'b', 'video', [mask])
        graph = Mock()

        # more complex, insert
        buildState = BuildState(edge,
                                np.random.randint(0, 255, (3984, 2988, 3), dtype=np.uint8),
                                np.random.randint(0, 255, (3884, 2888, 3), dtype=np.uint8),
                                np.zeros((3984, 2988), dtype=np.uint8),
                                (3984, 2988),
                                (3884, 2888),
                                directory='.',
                                compositeMask=cm,
                                pred_edges=None,
                                graph=graph)
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_composite:
            mock_composite.compositeMask = cm
            mock_composite.edge = edge
            mock_composite.arguments.return_value = edge['arguments']
            mock_composite.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 9900,
                'startframe': 100,
                'endtime': 11300,
                'endframe': 114,
                'frames': 15,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_composite)
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual([{'endframe': 99, 'rate': 10, 'starttime': 9000, 'error': 0, 'frames': 9, 'startframe': 91,
                               'endtime': 9800.0, 'type': 'video'},
                              {'endframe': 151, 'rate': 10, 'starttime': 11400, 'error': 0, 'frames': 37,
                               'startframe': 115,
                               'endtime': 15000, 'type': 'video'}],
                             result.videomasks
                             )

        # more complex, drop
        with patch('maskgen.mask_rules.BuildState', spec=buildState) as mock_donor:
            mock_donor.donorMask = cm
            mock_donor.edge = edge
            mock_donor.arguments.return_value = edge['arguments']
            mock_donor.isComposite = False
            mock_donor.getMasksFromEdge.return_value = [video_tools.create_segment(**{
                'starttime': 1400,
                'startframe': 15,
                'endtime': 2400,
                'endframe': 25,
                'frames': 11,
                'type': 'video',
                'rate': 10
            })]
            result = copy_paste_frames(mock_donor)
            # two because one was moved down...could combine them
            # but it matters little for our purposes.
            self.assertEqual(2, len(result.videomasks))
            self.assertEqual([{'endframe': 25, 'rate': 10, 'starttime': 1400, 'frames': 11, 'startframe': 15,
                               'endtime': 2400, 'type': 'video','error':0},
                              {'endframe': 151, 'rate': 10, 'starttime': 9000, 'error': 0, 'frames': 61,
                               'startframe': 91, 'endtime': 15000, 'type': 'video', 'error':0}],
                             result.videomasks)

    def test_compositeIdAssigner(self):
        G = nx.DiGraph(name="Empty")
        for i in xrange(1, 16):
            G.add_node(str(i), nodetype='base' if i == 1 else ('final' if i in [6, 7, 9, 10, 13] else 'intermediate'))
        G.add_edge('1', '2', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('2', '3', op='TransformAffine', recordInCompositeMask=False)
        G.add_edge('2', '4', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('3', '5', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('5', '6', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('5', '7', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('4', '8', op='TransformResize', recordInCompositeMask=False)
        G.add_edge('8', '9', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('8', '10', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('1', '11', op='OutputPng', recordInCompositeMask=False)
        G.add_edge('11', '12', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('12', '13', op='OutputPng', recordInCompositeMask=True)
        G.add_edge('5', '14', op='TransformResize', recordInCompositeMask=False)
        G.add_edge('14', '15', op='OutputPng', recordInCompositeMask=False)
        g = ImageGraphB(G)
        probe12branch1 = np.random.randint(0, 2, size=(10, 10))
        probe12branch2 = np.random.randint(0, 2, size=(10, 10))
        probe12branch3 = np.random.randint(0, 2, size=(12, 12))
        probe24branch2 = np.random.randint(0, 2, size=(10, 10))
        probe35 = np.random.randint(0, 2, size=(10, 10))
        probe35branch3 = np.random.randint(0, 2, size=(12, 12))
        probe56 = np.random.randint(0, 2, size=(10, 10))
        probe57 = np.random.randint(0, 2, size=(10, 10))
        probe89 = np.random.randint(0, 2, size=(10, 10))
        probe810 = np.random.randint(0, 2, size=(10, 10))
        probe1112 = np.random.randint(0, 2, size=(11, 11))
        probes = [Probe(('1', '2'), '10', '1', None, targetMaskImage=probe12branch2),
                  Probe(('1', '2'), '9', '1', None, targetMaskImage=probe12branch2),
                  Probe(('1', '2'), '6', '1', None, targetMaskImage=probe12branch1),
                  Probe(('1', '2'), '7', '1', None, targetMaskImage=probe12branch1),
                  Probe(('1', '2'), '15', '1', None, targetMaskImage=probe12branch3),
                  Probe(('2', '4'), '9', '1', None, targetMaskImage=probe24branch2),
                  Probe(('2', '4'), '10', '1', None, targetMaskImage=probe24branch2),
                  Probe(('3', '5'), '6', '1', None, targetMaskImage=probe35),
                  Probe(('3', '5'), '7', '1', None, targetMaskImage=probe35),
                  Probe(('3', '5'), '15', '1', None, targetMaskImage=probe35branch3),
                  Probe(('5', '6'), '6', '1', None, targetMaskImage=probe56),
                  Probe(('5', '7'), '7', '1', None, targetMaskImage=probe57),
                  Probe(('8', '9'), '9', '1', None, targetMaskImage=probe89),
                  Probe(('8', '10'), '10', '1', None, targetMaskImage=probe810),
                  Probe(('11', '12'), '13', '1', None, targetMaskImage=probe1112)
                  ]
        graphCompositeIdAssigner = GraphCompositeIdAssigner(g)
        probes = graphCompositeIdAssigner.updateProbes(probes, 'builder')
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
        self.assertEquals(index[(('1', '2'), '10')], index[(('1', '2'), '9')])
        self.assertEquals(index[(('2', '4'), '10')], index[(('2', '4'), '9')])
        self.assertNotEquals(index[(('1', '2'), '10')], index[(('1', '2'), '7')])
