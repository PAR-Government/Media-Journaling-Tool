from maskgen import graph_rules
import unittest
from maskgen.scenario_model import loadProject
from test_support import TestSupport
from mock import MagicMock, Mock
from maskgen.validation.core import Severity

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
        mockImage_frm = Mock(size=(3264, 4928))
        mockImage_to = Mock(size=(4928, 3264))
        r = graph_rules.checkSizeAndExif('Op', mockGraph, 'a', 'b')
        self.assertIsNone(r)
        mockImage_to.size = (3264, 4928)
        r = graph_rules.checkSizeAndExif('Op', mockGraph, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)
        mockGraph.get_edge.return_value = {'shape change': '(1664,-1664)','metadatadiff': [{'_rotate': [270]}]}
        r = graph_rules.checkSizeAndExif('Op', mockGraph, 'a', 'b')
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] == Severity.ERROR)



if __name__ == '__main__':
    unittest.main()
