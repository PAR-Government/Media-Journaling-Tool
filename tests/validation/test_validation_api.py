import unittest
from maskgen.validation.core import *
from tests.test_support import TestSupport
from maskgen.scenario_model import ImageProjectModel

from maskgen.maskgen_loader import MaskGenLoader
from mock import Mock
from maskgen.software_loader import insertCustomRule

class MockImageGraph:

    def __init__(self,name,nodes={}):
        self.name = name
        self.nodes= nodes
        self.api_validated_node = None

    def get_name(self):
        return self.name

    def get_node(self,name):
        return self.nodes[name]

    def setDataItem(self,item,checked_nodes,excludeUpdate=True):
        if item == 'api_validated_node':
            self.api_validated_node = checked_nodes

    def getDataItem(self,item,default_value):
        if item != 'api_validated_node':
            raise ValueError('Unexpected item {}'.format(item))
        return default_value

class MockValidationAPI(ValidationAPI):

    def __init__(self,preferences):
        self.testid = preferences['test.id']
        self.external = preferences['test.external']
        self.configured = preferences['test.configured']

    def isConfigured(self):
        """
        :return: return true if validator is configured an usable
        @rtype: bool
        """
        return self.configured

    def isExternal(self):
        return self.external

    def check_edge(self, op, graph, frm, to):
        """
        :param op: Operation structure
        :param graph: image graph
        :param frm: edge source
        :param to:  edge target
        :return:
        @type op: Operation
        @type graph: ImageGraph
        @type frm: str
        @type to: str
        """
        return [self.testid]

    def check_node(self, node, graph):
        """
        :param node: node id
        :param graph: image graph
        :return:
        @type node: str
        @type graph: ImageGraph
        """
        return [self.testid]

    def test(self):
        """
        :return: Error message if system is not configured properly otherwise None
        @rtype: str
        """
        return self.testid

    def get_journal_exporttime(self, journalname):
        """
        :param journalname:  name of the journal
        :return: export time of journal
        @type journalname: str
        @rtype: str
        """
        return self.testid


def test_rule_donor(op,graph,frm,to):
    return (Severity.ERROR, 'donor')

def test_rule_not_donor(op, graph, frm, to):
    return (Severity.ERROR,'not donor')

class TestValidationAPI(TestSupport):

    loader = MaskGenLoader()

    def setUp(self):
        self.loader.load()

    def test_configure(self):
        preferences = {}
        setValidators(preferences,[MockValidationAPI])
        c = ValidationAPIComposite({'test.configured': True,
                                    'test.external': False,
                                    'test.id': 'configured',
                                    })
        self.assertTrue(c.isConfigured())
        c = ValidationAPIComposite({'test.configured': False,
                                    'test.external': False,
                                    'test.id': 'configured',
                                    })
        self.assertFalse(c.isConfigured())

    def test_external(self):
        preferences = {}
        setValidators(preferences, [MockValidationAPI])
        c = ValidationAPIComposite({'test.configured': True,
                                    'test.external': True,
                                    'test.id': 'external',
                                    },external=True)
        self.assertTrue(c.isExternal())
        c = ValidationAPIComposite({'test.configured': True,
                                    'test.external': False,
                                    'test.id': 'external',
                                    })
        self.assertFalse(c.isExternal())

    def test_functions(self):
        preferences = {}
        setValidators(preferences, [MockValidationAPI])
        c = ValidationAPIComposite({'test.configured': True,
                                    'test.external': False,
                                    'test.id': 'functions',
                                    })
        self.assertEquals(['functions'], c.check_node(None,None))
        self.assertEquals(['functions'], c.check_edge(None,None,None,None))
        self.assertEquals('functions', c.get_journal_exporttime(None))
        self.assertEquals('functions', c.test())

    def test_journal(self):
        model = ImageProjectModel(self.locateFile('images/sample.json'))
        results = model.validate(external=False)


    def test_designation(self):
        from maskgen.software_loader import Operation
        opManager = Mock()
        insertCustomRule('test_rule_donor',test_rule_donor)
        insertCustomRule('test_rule_not_donor', test_rule_not_donor)
        operation = Operation('test', category='Test', includeInMask=False,
                                        rules={'donor:test_rule_donor','test_rule_not_donor'},
                                        optionalparameters={},
                                        mandatoryparameters={},
                                        description='test',
                                        generateMask='all',
                                        analysisOperations=[],
                                        transitions=[],
                                        compareparameters={})
        opManager.getAllOperations = Mock(return_value={'test':operation})
        opManager.getOperationWithGroups = Mock(return_value=operation)
        graph = Mock()
        graph.get_edge = Mock(return_value={'op':'test',
                                            'username':'test',
                                            'arguments': {},
                                            'metadatadiff': {}})
        graph.get_image = Mock(return_value=(0,self.locateFile('videos/sample1.mov')))

        validator = Validator(self.loader,opManager)
        results = validator.run_edge_rules(graph,'a','b', isolated=True)
        self.assertEqual(0, len([r for r in results if r.Module == 'test_rule_donor']))
        self.assertEqual(1, len([r for r in results if r.Module == 'test_rule_not_donor']))
        results = validator.run_edge_rules(graph, 'a', 'b', isolated=False)
        self.assertEqual(1, len([r for r in results if r.Module == 'test_rule_donor']))
        self.assertEqual(1, len([r for r in results if r.Module == 'test_rule_not_donor']))

    def test_browser_api(self):
        from datetime import datetime
        from maskgen.validation.browser_api import ValidationBrowserAPI
        setValidators(self.loader,[ValidationBrowserAPI])
        c = ValidationAPIComposite(preferences=self.loader,external=True)
        self.assertEquals(None,c.test())
        timeresult = c.get_journal_exporttime('023aeac56841a5961648798dfd491b16')
        datetime.strptime(timeresult, '%Y-%m-%d %H:%M:%S')
        graph = MockImageGraph('foo',
                               nodes={'023aeac56841a5961648798dfd491b16': {
                                      'file':'023aeac56841a5961648798dfd491b16.jpg','nodetype':'base'},
                                   'fdf9dfdsif': {
                                       'file': 'fdf9dfdsif.jpg', 'nodetype': 'base'},
                                   '06555b4024bf35fcda3705c34726f560': {
                                       'file': '06555b4024bf35fcda3705c34726f560.jpg', 'nodetype': 'final'}
                               })
        result = c.check_node('023aeac56841a5961648798dfd491b16',graph)
        self.assertTrue(result is None or len(result) == 0)
        result = c.check_node('fdf9dfdsif', graph)
        self.assertTrue('Cannot find base media file fdf9dfdsif.jpg in the remote system' in result[0][3])
        result = c.check_node('06555b4024bf35fcda3705c34726f560',graph)
        self.assertTrue('Final media node 06555b4024bf35fcda3705c34726f560.jpg used in journal 0e0a5952531104c7c21a53760403f051'
                          in result[0][3])

    def test_support_functions(self):
        messages = removeErrorMessages([
            ValidationMessage(Severity.ERROR,'','', 'big','mod1'),
            ValidationMessage(Severity.ERROR, '', '', 'bad','mod1'),
            ValidationMessage(Severity.ERROR, '', '', 'wolf','mod1')
        ],lambda x : x == 'big')
        self.assertTrue(hasErrorMessages(messages,lambda  x: x == 'bad'))
        self.assertTrue(hasErrorMessages(messages, lambda x: x == 'wolf'))
        messages = removeErrorMessages([
            ValidationMessage(Severity.WARNING, '', '', 'big', 'mod1'),
            ValidationMessage(Severity.WARNING, '', '', 'bad', 'mod1'),
            ValidationMessage(Severity.WARNING, '', '', 'wolf', 'mod1')
        ], lambda x: x == 'big')
        self.assertFalse(hasErrorMessages(messages, lambda x: x == 'bad'))
        self.assertFalse(hasErrorMessages(messages, lambda x: x == 'wolf'))

if __name__ == '__main__':
    unittest.main()
