from image_graph import ImageGraph
from tool_set import imageResizeRelative
import os

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
    Ouptut a graph to a PNG file
    """

    max_size = (125,125)
    def __init__(self, graph):
        """

        :param graph:
         @type graph : ImageGraph
        """
        self.graph = graph

    def outputToFile(self, file,options={}):
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
        self._draw(pluginName=('use_plugin_name' in options and options['use_plugin_name'])).write_png(filename)
        return filename

    def output(self, filename,options={}):
        """
        :param filename:
        :return:
        @type filename : str
         @rtype : str
        """
        if not filename.endswith('.png'):
            filename = filename + '.png'
        self._draw(pluginName=('use_plugin_name' in options and options['use_plugin_name'])).write_png(filename)
        return filename

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
            im,filename= self.graph.get_image(node_id)
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
            pydot_nodes[node_id] = pydot.Node(node_id,label=html,bgcolor=fillcolor,shape=shape)#,labelloc='t', image=prefix + '_thb.png',imagescale=True)
            pygraph.add_node(pydot_nodes[node_id])
        for edge_id in self.graph.get_edges():
            edge = self.graph.get_edge(edge_id[0],edge_id[1])
            label = edge['plugin_name'] if 'plugin_name' in edge and pluginName else edge['op']
            blue = "blue" if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'yes' else 'black'
            pygraph.add_edge(pydot.Edge(pydot_nodes[edge_id[0]],pydot_nodes[edge_id[1]],label=label, color = blue))
        return pygraph

