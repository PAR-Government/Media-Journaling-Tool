# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from image_graph import ImageGraph, createGraph
from maskgen import MaskGenLoader
from maskgen.external import api
from maskgen.external.api import BrowserAPI
from maskgen.support import getValue
from tool_set import imageResizeRelative, ImageWrapper, toIntTuple, openImage
import os
import tempfile
import numpy as np


class Fetcher:
    def __init__(self):
        pass

    def get_image(self, filename):
        """

        :param filename:
        :return:  image wrapper for image
        @rtype ImageWrapper
        """
        pass

    def get_url(self, filename):
        """

        :param filename:
        :return: URL to find image
        @rtype: str
        """
        pass

class UrlMediaFetcher(Fetcher):
    """
    Fectch URL and image using apiurl and apitoken using external Browser API
    """
    def __init__(self):
        Fetcher.__init__(self)
        settings = MaskGenLoader()
        self.token = settings.get_key('apitoken')
        self.url = settings.get_key('apiurl')
        self.temp_dir = tempfile.gettempdir()
        self.browserapi = BrowserAPI()

    def get_image(self, filename):
        """ Returns an image"""
        dl = api.download(filename, self.token, self.temp_dir, self.url)
        try:
            im = openImage(dl)
            return im
        finally:
            if os.path.exists(dl):
                os.remove(dl)

    def get_url(self, filename):
        filename = os.path.basename(filename).lower()
        return self.browserapi.get_url(filename)


class FileMediaFetcher(Fetcher):
    """
    Fectch URL and image from file system
    """
    def __init__(self):
        Fetcher.__init__(self)

    def get_image(self, filename):
        im = openImage(filename)
        return im

    def get_url(self, filename):
        return os.path.abspath(filename)


class FileMediaURLMixinFetcher(Fetcher):
    """
    Fectch URL from remote.
    Image from file system
    """
    def __init__(self,url_fetcher):
        Fetcher.__init__(self)
        self.url_fetcher = url_fetcher

    def get_image(self, filename):
        im = openImage(filename)
        return im

    def get_url(self, filename):
        return self.url_fetcher.get_url(os.path.basename(filename))


class GraphMediaHandler:
    """
    Resolve media using local graph (in a directory)
    """
    def __init__(self, media_fetcher=FileMediaFetcher()):
        self.media_fetcher = media_fetcher

    def get_image(self, graph, node_id):
        return graph.get_image(node_id)

    def get_url(self, graph, node_id):
        return self.media_fetcher.get_url(graph.get_pathname(node_id))


class ExternalMediaHandler:
    """
    Resolve media using remote images
    """
    def __init__(self, media_fetcher):
        self.media_fetcher = media_fetcher
        self.cache = {}

    def get_image(self, graph, node_id):
        filename = graph.get_filename(node_id)
        if len(graph.predecessors(node_id)) == 0 or len(graph.successors(node_id)) == 0:
            return self.media_fetcher.get_image(filename), os.path.join(graph.dir, filename)
        new_shape = self.determine_shape(graph, node_id)
        return ImageWrapper(np.zeros(new_shape, dtype=np.uint8)), os.path.join(graph.dir, filename)

    def get_url(self, graph, node_id):
        filename = graph.get_filename(node_id)
        path = self.media_fetcher.get_url(filename)
        return path

    def get_media_by_filename(self, filename):
        if filename in self.cache:
            return self.cache[filename]
        im = self.media_fetcher.get_image(filename)
        self.cache[filename] = im.image_array.shape[0:2]
        return im.image_array.shape[0:2]

    def determine_shape(self, graph, node_id):
        preds = graph.predecessors(node_id)
        if len(preds) == 0:
            return self.get_media_by_filename(graph.get_filename(node_id))
        for pred in preds:
            edge = graph.get_edge(pred, node_id)
            if edge['op'] != 'Donor':
                prior_shape = self.determine_shape(graph, pred)
                shape_change = toIntTuple(getValue(edge, 'shape_change', '(0,0)'))
                return prior_shape[0] + shape_change[0], prior_shape[1] + shape_change[1], 3
        return 500, 500, 3


def check_graph_status():
    import pydot
    try:
        pygraph = pydot.Dot(graph_type='digraph')
        pygraph.add_node(pydot.Node('test', label='test', shape='plain') )
        pygraph.write_png('check_graph_status.png')
        os.remove('check_graph_status.png')
    except Exception as ex:
        return 'pygraph failure: {}'.format(str(ex))


class ImageGraphPainter:

    """
    Ouptut a graph to a file using GraphViz
    """

    max_size = (125, 125)

    def __init__(self, graph, handler=GraphMediaHandler()):
        """

        :param graph:
         @type graph : ImageGraph
        """
        self.graph = graph
        self.handler = handler

    def outputToFile(self, _file, formats=['.png'], options={}):
        """
        :param options:
        :param formats: include .png, .cmapx, .gif, .imap.  See graphviz for formats
        :param file:
        :return:
        @type _file : file or str
        @rtype : str
        """
        if type(_file) is str:
            filename = _file
        else:
            _file.close()
            filename = _file.name

        return self.output(filename, formats, options)

    def output(self, filename, formats=['.png'], options={}):
        """
        :param filename:
        :param formats:
        :param options:
        :return: filename
        @type filename : str
        @type formats: list
        @type options: dict
        @rtype : None
        """
        dotgraph = self._draw(pluginName=('use_plugin_name' in options and options['use_plugin_name']))
        prefix = os.path.splitext(filename)[0]
        for f in formats:
            path = prefix + f
            dotgraph.write(path, format=f[1:])

        return None

    def _node_id_filename(self,node_id):
        import re
        return re.sub('[\(\)\&\:\-\? ]', '_', node_id) + '_thb.png'

    def _draw(self, pluginName=False):
        import pydot
        import cgi
        pydot_nodes = {}
        pygraph = pydot.Dot(graph_type='digraph')
        for node_id in self.graph.get_nodes():
            node = self.graph.get_node(node_id)
            iscgi = 'cgi' in node and node['cgi'] == 'yes'
            cgirefs = node['urls'] if 'urls' in node and len(node['urls']) > 0 else None
            if node['nodetype'] == 'final':
                shape = 'ellipse'
            else:
                shape = 'plain'
            fillcolor = 'turquoise' if 'experiment_id' in node else 'white'
            fillcolor = 'red' if iscgi else fillcolor
            im,filename= self.handler.get_image(self.graph, node_id)
            im = imageResizeRelative(im, self.max_size, self.max_size)
            im.touint8()
            prefix = os.path.split(filename)[0]
            fn = self._node_id_filename(node_id)
            im.save(os.path.join(prefix , fn))
            filename =  cgi.escape( node['file'])
            if cgirefs is not None:
                filename = cgirefs[0].split('/')[-1] + ('+{}'.format(len(cgirefs)-1) if len(cgirefs) > 1 else '')
            html = '<<TABLE border="0" cellborder="0" bgcolor="' + fillcolor + '"><TR><TD ><IMG SRC="' + \
                   os.path.join(prefix, fn) + '" scale="true"/></TD></TR><TR><td><font point-size="10">' + filename + '</font></td></TR></TABLE>>'
            href_path = self.handler.get_url(self.graph, node_id)
            pydot_nodes[node_id] = pydot.Node(node_id,label=html,bgcolor=fillcolor,shape=shape, href=href_path)
            # pydot_nodes[node_id] = pydot.Node(node_id,label=html,bgcolor=fillcolor,shape=shape)#,labelloc='t', image=prefix + '_thb.png',imagescale=True)
            pygraph.add_node(pydot_nodes[node_id])
        for edge_id in self.graph.get_edges():
            edge = self.graph.get_edge(edge_id[0],edge_id[1])
            label = edge['plugin_name'] if 'plugin_name' in edge and pluginName else edge['op']
            blue = "blue" if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'yes' else 'black'
            pygraph.add_edge(pydot.Edge(pydot_nodes[edge_id[0]],pydot_nodes[edge_id[1]],label='"' + label + '"', color = blue))
        return pygraph


def main(args):
    from maskgen.scenario_model import ImageProjectModel
    m = ImageProjectModel(args[1])
    p = ImageGraphPainter(m.getGraph(),handler=GraphMediaHandler(media_fetcher=FileMediaURLMixinFetcher(UrlMediaFetcher())))
    p.output(m.getName() + '.png',formats=['.png','.cmapx'])


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))
