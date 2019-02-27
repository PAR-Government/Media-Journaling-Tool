from maskgen import graph_rules
import unittest
from maskgen.scenario_model import loadProject
from test_support import TestSupport
from mock import MagicMock, Mock, patch
from maskgen.validation.core import Severity
from maskgen import video_tools
class TestToolSet(TestSupport):

    def test_aproject(self):
        model = loadProject(self.locateFile('images/sample.json'))
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


    def test_checkForVideoRetainment(self):
        graph = Mock()
        mapping = {'a':self.locateFile('videos/sample1.mov'), 'b':self.locateFile('videos/sample1.wav')}
        graph.get_image = lambda x:  (None, mapping[x])
        result = graph_rules.checkForVideoRetainment('op', graph, 'a', 'a')
        self.assertIsNone(result)
        result = graph_rules.checkForVideoRetainment('op', graph, 'a', 'b')
        self.assertIsNotNone(result)

    # Tests checkSame and checkBigger
    def test_checkLength(self):
        graph = Mock()
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': '1', 'End Time': '2', 'add type': 'insert'},
                                            'metadatadiff': {}})
        graph.get_image_path = Mock(return_value=self.locateFile('videos/sample1.mov'))
        graph.dir = '.'
        result = graph_rules.checkLengthSameOrBigger('op', graph, 'a', 'b')  # bigger
        self.assertIsNotNone(result)
        graph.get_edge.return_value['metadatadiff'] ={'video': {'nb_frames': ('change', '2', '1')}}
        result = graph_rules.checkLengthSameOrBigger('op', graph, 'a', 'b')
        self.assertIsNotNone(result)
        graph.get_edge.return_value['metadatadiff'] = {'video': {'nb_frames': ('change', '1', '2')}}
        result = graph_rules.checkLengthSameOrBigger('op', graph, 'a', 'b')
        self.assertIsNone(result)
        graph.get_edge.return_value['arguments']['add type'] = 'replace'
        result = graph_rules.checkLengthSameOrBigger('op', graph, 'a', 'b')  # same
        self.assertIsNotNone(result)
        graph.get_edge.return_value['metadatadiff'] = {}
        result = graph_rules.checkLengthSameOrBigger('op', graph, 'a', 'b')
        self.assertIsNone(result)
        result = graph_rules.checkLengthSmaller('op', graph, 'a', 'b') # smaller
        self.assertIsNotNone(result)
        graph.get_edge.return_value['metadatadiff'] = {'video': {'nb_frames': ('change', '2', '1')}}
        result = graph_rules.checkLengthSmaller('op', graph, 'a', 'b')
        self.assertIsNone(result)
        graph.get_edge.return_value['metadatadiff'] = {'video': {'nb_frames': ('change', '1', '2')}}
        result = graph_rules.checkLengthSmaller('op', graph, 'a', 'b')
        self.assertIsNotNone(result)

    def test_checkAudioLengthBigger(self):
        graph = Mock()
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'video':{'duration':('change',1,2)}}})
        graph.get_image_path = Mock(return_value=self.locateFile('videos/sample1.mov'))
        graph.get_node = Mock(return_value={'file': self.locateFile('videos/sample1.mov')})
        graph.dir = '.'
        result = graph_rules.checkAudioLengthBigger('op', graph, 'a', 'b')
        self.assertIsNotNone(result)
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'audio': {'duration': ('change', 1, 1)}}})
        result = graph_rules.checkAudioLengthBigger('op', graph, 'a', 'b')
        self.assertIsNotNone(result)
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'audio': {'duration': ('change', 1, 2)}}})
        result = graph_rules.checkAudioLengthBigger('op', graph, 'a', 'b')
        self.assertIsNone(result)

    def test_checkAudioLengthSmaller(self):
        graph = Mock()
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'video':{'duration':('change',1,2)}}})
        graph.get_image_path = Mock(return_value=self.locateFile('videos/sample1.mov'))
        graph.get_node = Mock(return_value={'file': self.locateFile('videos/sample1.mov')})
        graph.dir = '.'
        result = graph_rules.checkAudioLengthSmaller('op', graph, 'a', 'b')
        self.assertIsNotNone(result)
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'audio': {'duration': ('change', 1, 1)}}})
        result = graph_rules.checkAudioLengthSmaller('op', graph, 'a', 'b')
        self.assertIsNotNone(result)
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'audio': {'duration': ('change', 2, 1)}}})
        result = graph_rules.checkAudioLengthSmaller('op', graph, 'a', 'b')
        self.assertIsNone(result)

    def test_checkAudioLengthDonor(self):
        graph = Mock()
        def which_edge(x,y):
            if x in ['ai','ar']:
                return {'arguments': {'Start Time': 1, 'End Time': 2,
                                      'add type':'insert' if x == 'ai' else 'replace'},
                        'op':'AddAudioOfSomeType',
                                            'metadatadiff': {'video': {'duration': ('change', 1, 2)}}}
            else:
                return {'arguments': {'Start Time': 4, 'End Time': 5, 'add type': 'insert'},
                        'op':'Donor',
                        'videomasks': [{'startframe': 20,'endframe':30,'rate':10,'type':'audio','frames':11,
                         'starttime':1900,'endtime':2900}]}
        graph.get_edge = which_edge
        graph.get_image_path = Mock(return_value=self.locateFile('videos/sample1.mov'))
        graph.get_node = Mock(return_value={'file': self.locateFile('videos/sample1.mov')})
        graph.dir = '.'
        graph.predecessors = Mock(return_value=['ai','c'])
        def duration(x,audio=True):
            return {'ai': 59348.345, 'b':60348.345}[x.source]
        with patch('maskgen.video_tools.get_duration',spec=duration) as cm:
            cm.side_effect = duration
            result = graph_rules.checkAudioLengthDonor('op', graph, 'ai', 'b')
            self.assertIsNone(result)

        with patch('maskgen.video_tools.get_duration',spec=duration) as cm:
            cm.side_effect = duration
            result = graph_rules.checkAudioLengthDonor('op', graph, 'ar', 'b')
            self.assertIsNotNone(result)

        def duration(x,audio=True):
            return {'ai': 59348.345, 'b':1000.0}[x.source]
        with patch('maskgen.video_tools.get_duration',spec=duration) as cm:
            cm.side_effect = duration
            result = graph_rules.checkAudioLengthDonor('op', graph, 'ar', 'b')
            self.assertIsNone(result)



    def test_checkAudioLength(self):
        graph = Mock()
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'video':{'duration':('change',1,2)}}})
        graph.get_image_path = Mock(return_value=self.locateFile('videos/sample1.mov'))
        graph.get_node = Mock(return_value={'file': self.locateFile('videos/sample1.mov')})
        graph.dir = '.'
        result = graph_rules.checkAudioLength('op', graph, 'a', 'b')
        self.assertEqual(0,result)
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'audio': {'x': ('change', 1, 1)}}})
        result = graph_rules.checkAudioLength('op', graph, 'a', 'b')
        self.assertEqual(0, result)
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'audio': {'duration': ('change', 2, 1)}}})
        result = graph_rules.checkAudioLength('op', graph, 'a', 'b')
        self.assertEqual(1, result)

    def test_checkSampleRate(self):
        graph = Mock()
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'audio': {'sample_rate': ('change', 1, 2)}}})
        graph.get_image_path = Mock(return_value=self.locateFile('videos/sample1.mov'))
        graph.get_node = Mock(return_value={'file': self.locateFile('videos/sample1.mov')})
        graph.dir = '.'
        result = graph_rules.checkSampleRate('op', graph, 'a', 'b')
        self.assertIsNotNone(result)
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'audio': {'avr_rate': ('change', 1, 2)}}})
        graph.get_image_path = Mock(return_value=self.locateFile('videos/sample1.mov'))
        graph.get_node = Mock(return_value={'file': self.locateFile('videos/sample1.mov')})
        graph.dir = '.'
        result = graph_rules.checkSampleRate('op', graph, 'a', 'b')
        self.assertIsNone(result)

    def test_checkAudioOnly(self):
        graph = Mock()
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'video':{'duration':('change',1,2)}}})
        graph.get_image_path = Mock(return_value=self.locateFile('videos/sample1.mov'))
        graph.get_node = Mock(return_value={'file': self.locateFile('videos/sample1.mov')})
        graph.dir = '.'
        result = graph_rules.checkAudioOnly('op', graph, 'a', 'b')
        self.assertIsNone(result)
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'video': {'nb_frames': ('change', 1, 2)}}})
        result = graph_rules.checkAudioOnly('op', graph, 'a', 'b')
        self.assertIsNotNone(result)
        graph.get_edge = Mock(return_value={'arguments': {'Start Time': 1, 'End Time': 2},
                                            'metadatadiff': {'audio': {'duration': ('change', 2, 1)}}})
        result = graph_rules.checkAudioOnly('op', graph, 'a', 'b')
        self.assertIsNone(result)

    def test_checkCropLength(self):
        graph = Mock()
        graph.get_edge = Mock(return_value={'arguments': {'Start Time':1,'End Time':2},
                                            'metadatadiff':{}})
        graph.get_image_path = Mock(return_value=self.locateFile('videos/sample1.mov'))
        graph.get_node = Mock(return_value= {'file':self.locateFile('videos/sample1.mov')})
        graph.dir = '.'
        result = graph_rules.checkCropLength('op', graph, 'a', 'b')
        self.assertIsNotNone(result)
        self.assertTrue('803' in result[1])

    def test_fileTypeChanged(self):
        graph = Mock()
        values= {'a': self.locateFile('images/hat.jpg'),
                 'b': self.locateFile('images/sample.jpg'),
                 'c': self.locateFile('tests/videos/sample1.mov')}
        def side_effect(x):
            return 0,values[x]
        graph.get_image = Mock(side_effect=side_effect)
        self.assertIsNone(graph_rules.checkFileTypeChange('op',graph,'a','b'))
        graph.get_image.assert_called_with('b')
        self.assertIsNotNone(
            graph_rules.checkFileTypeChange('op',graph,'a','c'))
        graph.get_image.assert_called_with('c')

    def test_checkCutFrames(self):
        def edge(a,b):
            return {}
        def get_node(a):
            return {'file':a}
        def get_image_path(a):
            return a
        mock = Mock()
        mock.get_edge = Mock(spec=edge,return_value={
         'videomasks': [{'startframe': 20,'endframe':30,'rate':10,'type':'audio','frames':11,
                         'starttime':1900,'endtime':2900},
                        {'startframe': 20, 'endframe': 30, 'rate': 10, 'type': 'video', 'frames': 11,
                         'starttime': 1900, 'endtime': 2900}
                        ]
        })
        mock.get_node =get_node
        mock.get_image_path = get_image_path
        mock.dir = '.'
        video_tools.meta_cache[video_tools.meta_key(video_tools.FileMetaDataLocator('a'), start_time_tuple=(0,1), end_time_tuple=None, media_types=['video'],
                                 channel=0)] = [{'startframe': 1,'endframe':300,'rate':10,'type':'audio','frames':300,
                         'starttime':0,'endtime':29900}]
        video_tools.meta_cache[video_tools.meta_key(video_tools.FileMetaDataLocator('b'), start_time_tuple=(0,1), end_time_tuple=None, media_types=['video'],
                                 channel=0)] = [{'startframe': 1,'endframe':289,'rate':10,'type':'audio','frames':289,
                         'starttime':0,'endtime':28800}]
        video_tools.meta_cache[
            video_tools.meta_key(video_tools.FileMetaDataLocator('a'), start_time_tuple=(0, 1), end_time_tuple=None, media_types=['audio'],
                                 channel=0)] = [
            {'startframe': 1, 'endframe': 300, 'rate': 10, 'type': 'video', 'frames': 300,
             'starttime': 0, 'endtime': 29900}]
        video_tools.meta_cache[
            video_tools.meta_key(video_tools.FileMetaDataLocator('b'), start_time_tuple=(0, 1), end_time_tuple=None, media_types=['audio'],
                                 channel=0)] = [
            {'startframe': 1, 'endframe': 270, 'rate': 10, 'type': 'video', 'frames': 270,
             'starttime': 0, 'endtime': 26900}]
        r = graph_rules.checkCutFrames('op',mock,'a','b')
        self.assertEqual(2, len(r))
        self.assertTrue('3000' in r[1])


    def test_checkForSelectFrames(self):
        def preds(a):
            pass
        mock = Mock()
        mock.predecessors = Mock(spec=preds,return_value=['a','d'])
        mock.findOp = Mock(return_value=False)
        r = graph_rules.checkForSelectFrames('op',mock,'a','b')
        self.assertEqual(2, len(r))
        self.assertEqual(Severity.WARNING,r[0])
        mock.predecessors.assert_called_with('b')
        mock.findOp.assert_called_once_with('d', 'SelectRegionFromFrames')

        mock = Mock()
        mock.predecessors = Mock(spec=preds, return_value=['a', 'd'])
        mock.findOp = Mock(return_value=True)
        r = graph_rules.checkForSelectFrames('op', mock, 'a', 'b')
        self.assertIsNone(r)
        mock.predecessors.assert_called_with('b')
        mock.findOp.assert_called_once_with('d', 'SelectRegionFromFrames')

    def test_checkAudioOutputType(self):
        op_mock = Mock()
        op_mock.name = 'OutputAudioPCM'
        graph_mock = Mock()
        graph_mock.get_node = Mock(return_value={'file':'foo.png'})
        graph_mock.dir = '.'
        r = graph_rules.checkAudioOutputType(op_mock, graph_mock, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)
        graph_mock.get_node.assert_called_with('b')
        graph_mock.get_node = Mock(return_value={'file':'foo.wav'})
        r = graph_rules.checkAudioOutputType(op_mock, graph_mock, 'a', 'b')
        self.assertIsNone(r)

    def test_checkFileTypeUnchanged(self):
        op_mock = Mock()
        op_mock.name = 'OutputCopy'
        graph_mock = Mock()
        graph_mock.get_node = lambda x: {'file':'x.png'} if x == 'a' else {'file':'y.pdf'}
        graph_mock.dir = '.'
        r = graph_rules.checkFileTypeUnchanged(op_mock, graph_mock, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)
        graph_mock.get_node = Mock(return_value={'file':'foo.wav'})
        r = graph_rules.checkFileTypeUnchanged(op_mock, graph_mock, 'a', 'b')
        self.assertIsNone(r)

    def test_checkOutputType(self):
        op_mock = Mock()
        op_mock.name='OutputPDF'
        graph_mock = Mock()
        graph_mock.get_image_path = Mock(return_value='foo.png')
        r = graph_rules.checkOutputType(op_mock, graph_mock, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)
        graph_mock.get_image_path.assert_called_with('b')
        graph_mock.get_image_path = Mock(return_value='foo.pdf')
        r = graph_rules.checkOutputType(op_mock, graph_mock, 'a', 'b')
        self.assertIsNone(r)

    def test_checkJpgOutputType(self):
        op_mock = Mock()
        op_mock.name='OutputMp4'
        graph_mock = Mock()
        graph_mock.get_image_path = Mock(return_value='foo.png')
        r = graph_rules.checkJpgOutputType(op_mock, graph_mock, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)
        graph_mock.get_image_path.assert_called_with('b')
        graph_mock.get_image_path = Mock(return_value='foo.jpg')
        r = graph_rules.checkJpgOutputType(op_mock, graph_mock, 'a', 'b')
        self.assertIsNone(r)

    def test_checkMp4OutputType(self):
        op_mock = Mock()
        op_mock.name='OutputMp4'
        graph_mock = Mock()
        graph_mock.get_image_path = Mock(return_value='foo.png')
        r = graph_rules.checkMp4OutputType(op_mock, graph_mock, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)
        graph_mock.get_image_path.assert_called_with('b')
        graph_mock.get_image_path = Mock(return_value='foo.mpeg')
        r = graph_rules.checkMp4OutputType(op_mock, graph_mock, 'a', 'b')
        self.assertIsNone(r)

    def test_checkSize(self):
        mock = Mock()
        mock.get_edge = Mock(return_value={'shape change': '(20,20)'})
        r = graph_rules.checkSize('Op', mock, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)
        mock.get_edge.return_value = {}
        r = graph_rules.checkSize('Op', mock, 'a', 'b')
        self.assertIsNone(r)

    def test_checkSizeAndExif(self):

        def get_MockImage(name, metadata=dict()):
            if name == 'a':
                return mockImage_frm, name
            else:
                return mockImage_to, name

        mockGraph = Mock(get_edge = Mock(return_value={'shape change': '(1664,-1664)',
                                                       'exifdiff':{'Orientation': ['add', 'Rotate 270 CW']}}),
                         get_image=get_MockImage)
        mockImage_frm = Mock(size=(3264, 4928),isRaw=False)
        mockImage_to = Mock(size=(4928, 3264), isRaw=False)
        r = graph_rules.checkSizeAndExif('Op', mockGraph, 'a', 'b')
        self.assertIsNone(r)
        mockImage_to.size = (3264, 4928)
        r = graph_rules.checkSizeAndExif('Op', mockGraph, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)
        mockGraph.get_edge.return_value = {'shape change': '(1664,-1664)','metadatadiff': {'video':{'_rotate': ('change',90,270)}}}
        r = graph_rules.checkSizeAndExif('Op', mockGraph, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)

    def test_checkSizeAndExifPNG(self):

        def get_MockImage(name, metadata=dict()):
            if 'arw' in name:
                if name[0] == 'a':
                    return mockImage_frm_raw, name
                else:
                    return mockImage_to_raw, name

            if name[0] == 'a':
                return mockImage_frm, name
            else:
                return mockImage_to, name

        mockGraph = Mock(get_edge = Mock(return_value={'shape change': '(1664,-1664)',
                                                       'arguments' : {'Image Rotated':'yes'},
                                                       'exifdiff':{'Orientation': ['add', 'Rotate 270 CW']}}),
                         get_image=get_MockImage)
        mockImage_frm = Mock(size=(3264, 4928), isRaw=False)
        mockImage_to = Mock(size=(4928, 3264), isRaw=False)
        mockImage_frm_raw = Mock(size=(3264, 4928), isRaw=True)
        mockImage_to_raw = Mock(size=(4928, 3264), isRaw=True)
        r = graph_rules.checkSizeAndExifPNG('Op', mockGraph, 'a.jpg', 'b.jpg')
        self.assertIsNone(r)
        mockImage_to.size = (3264, 4928)
        r = graph_rules.checkSizeAndExifPNG('Op', mockGraph, 'a.jpg', 'b.jpg')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)

        mockGraph = Mock(get_edge=Mock(return_value={'shape change': '(-50,-50)',
                                                    'arguments': {'Image Rotated': 'no'}}),
                         get_image=get_MockImage)

        mockImage_to_raw.size = (3214, 4878)
        r = graph_rules.checkSizeAndExifPNG('Op', mockGraph, 'a.arw', 'b.arw')
        self.assertIsNone(r)


        mockImage_to_raw.size = (3000, 4800)
        r = graph_rules.checkSizeAndExifPNG('Op', mockGraph, 'a.arw', 'b.arw')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)

        mockGraph = Mock(get_edge=Mock(return_value={'shape change': '(-50,-50)',
                                                     'arguments': {'Image Rotated': 'no',
                                                                    'Lens Distortion Applied': 'yes'}}),
                         get_image=get_MockImage)

        mockImage_to_raw.size = (3000, 4800)
        r = graph_rules.checkSizeAndExifPNG('Op', mockGraph, 'a.arw', 'b.arw')
        self.assertIsNone(r)

        mockImage_to.size = (3214, 4878)
        r = graph_rules.checkSizeAndExifPNG('Op', mockGraph, 'a.jpg', 'b.jpg')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)

        mockGraph.get_edge.return_value = {'shape change': '(-30,-30)'}
        mockImage_to.size = (3234, 4898)
        r = graph_rules.checkSizeAndExifPNG('Op', mockGraph, 'a.jpg', 'b.jpg')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)

        mockGraph.get_edge.return_value = {'shape change': '(-30,-30)','arguments': {'Lens Distortion Applied':'yes'}}
        mockImage_to.size = (3234, 4898)
        r = graph_rules.checkSizeAndExifPNG('Op', mockGraph, 'a.jpg', 'b.jpg')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)

        mockGraph.get_edge.return_value = {'shape change': '(-100,-100)'}
        mockImage_to.size = (3164, 4828)
        r = graph_rules.checkSizeAndExifPNG('Op', mockGraph, 'a.jpg', 'b.jpg')
        self.assertTrue(len(r)> 0)
        self.assertTrue(r[0] == Severity.ERROR)

    def test_checkMoveMask(self):
        import numpy as np
        from maskgen.tool_set import GrayFrameWriter, GrayBlockWriter
        from maskgen.image_wrap import ImageWrapper

        def edge(a,b):
            return {}

        mask = np.ones((1092, 720), dtype='uint8') * 255
        mask[100:250, 100:200] = 0
        ImageWrapper(mask).save(filename='.\\test_jt_mask.png')
        self.addFileToRemove(filename='.\\test_jt_mask.png')

        input_mask = np.zeros((1092, 720, 3), dtype='uint8')
        input_mask[100:200, 100:200, :] = 255
        ImageWrapper(input_mask).save(filename='.\\test_input_mask.png')
        self.addFileToRemove(filename='.\\test_input_mask.png')

        mockGraph = Mock(get_edge=Mock(return_value={'inputmaskname': self.locateFile('test_input_mask.png'),
                                                     'maskname': self.locateFile('test_jt_mask.png')}))
        mockGraph.dir = '.'
        r = graph_rules.checkMoveMask('Op', mockGraph, 'a', 'b')
        self.assertIsNone(r)

        input_mask = np.zeros((1092, 720, 3), dtype='uint8')
        input_mask[150:250, 150:250, :] = 255
        ImageWrapper(input_mask).save(filename='.\\test_input_mask.png')
        self.addFileToRemove(filename='.\\test_input_mask.png')

        r = graph_rules.checkMoveMask('Op', mockGraph, 'a', 'b')
        self.assertIsNotNone(r)

        w = GrayBlockWriter('test_jt', 10)
        m = np.ones((1092, 720), dtype='uint8') * 255
        m[100:250, 100:200] = 0
        for i in range(60):
            w.write(m, i / 10.0, i)
        w.close()
        self.addFileToRemove(w.filename)

        w = GrayFrameWriter('test_input', 10)
        m = np.zeros((1092, 720, 3), dtype='uint8')
        m[100:200, 100:200, :] = 255
        for i in range(60):
            w.write(m, i / 10.0, 0)
        w.close()
        self.addFileToRemove(w.filename)

        mockGraph.get_edge = Mock(spec=edge, return_value={ 'inputmaskname': self.locateFile('test_input_mask_0.avi'),
            'videomasks': [{'startframe': 1, 'endframe': 60, 'rate': 10, 'type': 'video', 'frames': 60,
                            'videosegment':'test_jt_mask_0.0.hdf5', 'starttime': 0, 'endtime': 600},
                           ]
        })

        r = graph_rules.checkMoveMask('Op', mockGraph, 'a', 'b')
        self.assertIsNone(r)

        w = GrayFrameWriter('test_input', 10)
        m = np.zeros((1092, 720, 3), dtype='uint8')
        m[150:250, 150:250, :] = 255
        for i in range(60):
            w.write(m, i / 10.0, 0)
        w.close()
        self.addFileToRemove(w.filename)

        r = graph_rules.checkMoveMask('Op', mockGraph, 'a', 'b')
        self.assertIsNotNone(r)

if __name__ == '__main__':
    unittest.main()
