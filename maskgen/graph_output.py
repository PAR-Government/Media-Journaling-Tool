from image_graph import ImageGraph
from tool_set import imageResizeRelative
import os

class ImageGraphPainter:

    """
    Ouptut a graph to a PNG file
    """

    max_size = (125,125)
    def __init__(self, graph):
        """

        :param graph:
         @type graph : ImageGraph
        """
        self.graph = graph

    def outputToFile(self, file):
        """
        :param file:
        :return:
        @type file : file
        @rtype : str
        """
        if type(file) is str:
            filename = file
        else:
            file.close()
            filename = file.name
        if not filename.endswith('.png'):
            filename = filename + '.png'
        self._draw().write_png(filename)
        return filename

    def output(self, filename):
        """
        :param filename:
        :return:
        @type filename : str
         @rtype : str
        """
        if not filename.endswith('.png'):
            filename = filename + '.png'
        self._draw().write_png(filename)
        return filename

    def _node_id_filename(self,node_id):
        import re
        return re.sub('[\(\)\&\:\-\? ]', '_', node_id) + '_thb.png'

    def _draw(self):
        import pydot
        import cgi
        pydot_nodes = {}
        pygraph = pydot.Dot(graph_type='digraph')
        for node_id in self.graph.get_nodes():
            node = self.graph.get_node(node_id)
            im,filename= self.graph.get_image(node_id)
            im = imageResizeRelative(im, self.max_size, self.max_size)
            prefix = os.path.split(filename)[0]
            fn = self._node_id_filename(node_id)
            im.save(os.path.join(prefix , fn))
            html = '<<TABLE border="0" cellborder="0"><TR><TD ><IMG SRC="' + \
                   os.path.join(prefix, fn) + '" scale="true"/></TD></TR><TR><td><font point-size="10">' + cgi.escape( node['file']) + '</font></td></TR></TABLE>>'
            pydot_nodes[node_id] = pydot.Node(node_id,label=html,shape='plain')#,labelloc='t', image=prefix + '_thb.png',imagescale=True)
            pygraph.add_node(pydot_nodes[node_id])
        for edge_id in self.graph.get_edges():
            edge = self.graph.get_edge(edge_id[0],edge_id[1])
            blue = "blue" if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'yes' else 'black'
            pygraph.add_edge(pydot.Edge(pydot_nodes[edge_id[0]],pydot_nodes[edge_id[1]],label=edge['op'], color = blue))
        return pygraph
