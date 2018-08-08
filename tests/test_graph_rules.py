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

if __name__ == '__main__':
    unittest.main()
