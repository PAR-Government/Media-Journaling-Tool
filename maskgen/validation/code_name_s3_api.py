# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from maskgen.software_loader import getFileName,getMetDataLoader
from maskgen.image_graph import ImageGraph
from core import ValidationAPI,ValidationMessage,Severity

loader = getMetDataLoader()

class ValidationCodeNameS3(ValidationAPI):

    filename = 'ManipulatorCodeNames.txt'

    def __init__(self,preferences):
        ValidationAPI.__init__(self,preferences)
        self.names = []
        self.reload()

    def reload(self):
        self.names = loader.manipulator_names

    def isExternal(self):
        return False

    def isConfigured(self):
        """
        :return: return true if validator is configured an usable
        @rtype: bool
        """
        return self.names is not None

    def check_graph(self,graph):
        """
        Graph meta-data level errors only
        :param graph: image graph
        :return:
        @type graph: ImageGraph
        """
        if  graph.getDataItem('username','') not in self.names:
            return [ValidationMessage(Severity.ERROR,
                                      '',
                                      '',
                                      'user name {} not valid'.format(graph.getDataItem('username','')),
                                      'User',
                                      None)]
        return []

    def check_edge(self, op, graph, frm, to):
        """
        :param op: Operation structure
        :param graph: image graph
        :param frm: edge source
        :param to:  edge target
        :return: list of (severity,str)
        @type op: Operation
        @type graph: ImageGraph
        @type frm: str
        @type to: str
        @rtype: list of (Severity,str)
        """
        edge = graph.get_edge(frm,to)
        if  edge['username'] not in self.names:
            return [ValidationMessage(Severity.ERROR,
                                      frm,
                                      to,
                                      'user name {} not valid'.format( edge['username']),
                                      'User',
                                      None)]
        return []

    def check_node(self, node, graph):
        """
        :param node: node id
        :param graph: image graph
        :return: list of (severity,str)
        @type node: str
        @type graph: ImageGraph
        @rtype: list of (Severity,str)
        """
        return []

    def test(self):
        return None if self.isConfigured() else 'Checking usernames not configured.  Missing ' + ValidationCodeNameS3.filename



ValidationAPI.register(ValidationCodeNameS3)