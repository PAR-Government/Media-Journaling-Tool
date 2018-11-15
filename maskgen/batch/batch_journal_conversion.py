# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
from maskgen.batch import batch_project
from maskgen.scenario_model import ImageProjectModel
from maskgen.software_loader import getMetDataLoader, ProjectProperty, getOperation
from maskgen.support import getValue
from maskgen.image_graph import ImageGraph
import json
import argparse
import sys


class BatchConverter:

    """
    Convert Journals into Batch Project Specifications.
    Supports a shell command line interface as well.
    """

    def __init__(self,model):
        """
               :param model: ImageProjectModel
               :return:
               @type model: ImageProjectModel
         """
        self.model = model
        self._reset()

    def convert(self,name=None):
        """
        :param name: optional project name
        :return: the dictionary used to represent the graph
        @type name: str
        @rtype dict:
        """
        self._convertGraph(name=name)
        self._convertNodes()
        self._convertEdges()
        return self._assembleGraph()

    def convertAndSave(self,filename=None,name=None):
        """
        :param filename:  optional final name  (JSON).  The prject name is used if not provided
        :param name: optional project name
        :return: the dictionary used to represent the graph
        @type str: name
        @rtype dict:
        """
        graph_name = self._convertGraph(name=name)
        self._convertNodes()
        self._convertEdges()
        file_to_use = graph_name + '.json' if filename is None else filename
        graph = self._assembleGraph()
        with open(file_to_use, 'w') as fp:
            json.dump(graph, fp, indent=2, encoding='utf-8')
        return graph

    def _reset(self):
        self.id = 1
        self.nodes = {}
        self.graph_section = {}
        self.id_mapping  = {}

    def toID(self,name):
        self.id+=1
        return '%s_%d' % (name, self.id)

    def _convertGraph(self,name=None):
        properties = getMetDataLoader().projectProperties
        properties = [prop for prop in properties if not prop.node and not prop.semanticgroup and not prop.readonly]
        self.graph_section = {}
        for prop in properties:
            graph_data = self.model.getGraph().getMetadata()
            if prop.name in graph_data:
                self.graph_section[prop.name] = graph_data[prop.name]
        if name is not None:
            self.graph_section['name'] = name
        else:
            self.graph_section['name'] = self.model.getName()
        return name

    def _convertNodes(self):
        """
        :param graph:
        :return:
        @type graph: ImageGraph
        """
        graph = self.model.getGraph()
        for node_id in graph.get_nodes():
            node = graph.get_node(node_id)
            new_node = None
            if node['nodetype'] == 'base':
                new_node = {}
                new_node['op_type'] = 'BaseSelection'
                new_node['image_directory'] = '{image_directory}'
                new_node['pickist'] = 'base_picklist'
                new_node['id'] = self.toID('base')
            elif node['nodetype'] == 'donor':
                new_node = {}
                new_node['op_type'] = 'ImageSelectionPluginOperation'
                new_node['plugin'] = 'PickPairedImage'
                new_node['id'] = self.toID('donor')
                image_dir = "{donor_%s_dir}" % new_node['id']
                arguments =  {
                    "directory": {
                        "type": "value",
                        "value": image_dir
                    },
                    "pairing": {
                        "type": "value",
                        "value": "%s/pairedimages.csv" % image_dir
                    }
                }
                new_node['arguments'] = arguments
            if new_node is not None:
                self.nodes[new_node['id']] = new_node
                self.id_mapping[node_id] = new_node['id']

    def _convertEdges(self):
        graph = self.model.getGraph()
        for edge_id in graph.get_edges():
            edge = graph.get_edge(edge_id[0], edge_id[1])
            op = edge['op']
            if op.lower() != 'donor':
                new_operation_node = self._convertEdge(edge)
                self.nodes[new_operation_node['id']] = new_operation_node
                self.id_mapping[edge_id[1]] = new_operation_node['id']

    def _convertEdge(self,edge):
        """
        :param edge:
        :return: new for edge
        """
        new_operation_node = {}
        if 'plugin_name' in edge:
            new_operation_node['op_type'] = 'PluginOperation'
            new_operation_node['id'] = self.toID(edge['plugin_name'])
            new_operation_node['plugin'] = edge['plugin_name']
        else:
            new_operation_node['op_type'] = 'PreProcessedMediaOperation'
            new_operation_node['id'] = self.toID(edge['op'])
            op = getOperation(edge['op'],fake=True)
            new_operation_node['category'] = op.category
            new_operation_node['op'] = op.name
            new_operation_node['software'] = edge['softwareName']
            new_operation_node['software version'] = edge['softwareVersion']
            new_operation_node['description'] = edge['description']
            semanticGroups = getValue(edge,'semanticGroups',None)
            if semanticGroups is not None and len(semanticGroups) > 0:
                new_operation_node['semanticGroups'] = semanticGroups
            new_operation_node['directory'] = "{" +  new_operation_node['id'] + "}".replace(' ','_')
            if 'recordMaskInComposite' in edge:
                new_operation_node['recordMaskInComposite'] = edge['recordMaskInComposite']
        arguments = {}
        for k, v in getValue(edge, 'arguments', {}).iteritems():
            if k  in ['function','video_function','audio_function']:
                continue
            value = self._convertArgument(v)
            if value is not None:
                arguments[k] = value
        new_operation_node['arguments'] = arguments
        return new_operation_node

    def _convertArgument(self,value):
        return {'type':'value','value':value}

    def _assembleGraph(self):
        graph = self.model.getGraph()
        links = []
        for edge_id in graph.get_edges():
            edge = graph.get_edge(edge_id[0], edge_id[1])
            op = edge['op']
            source = self.id_mapping[edge_id[0]]
            target = self.id_mapping[edge_id[1]]
            if op.lower() == 'donor':
                target_node = self.nodes[target]
                target_node['arguments'].update({
                    'type':'donor',
                    'source':source
                })
                links.append({'source': source, 'target': target,'donor':True})
            else:
                links.append({'source': source, 'target':target})
        return  {
            "directed": True,
            "graph": self.graph_section,
            "nodes": self.nodes.values(),
            "links": links,
            "is_multigraph": False
        }

def main(argv=sys.argv[1:]):
    from maskgen.batch.batch_project import BatchProject
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', required=True, help='JSON of Journal Project')
    parser.add_argument('--name', required=False, help='Name for Batch Project')
    args = parser.parse_args(argv)
    model = ImageProjectModel(args.json)
    converter = BatchConverter(model)
    batch = converter.convertAndSave(name=args.name)
    bp = BatchProject(batch)
    bp.saveGraphImage('.',use_id=True)

if __name__ == '__main__':
    main(sys.argv[1:])
