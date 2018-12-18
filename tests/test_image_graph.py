from maskgen import image_graph
import unittest
from test_support import TestSupport
import os
import shutil

class TestImageGraph(TestSupport):

   def test_filetype(self):
      graph = image_graph.createGraph(self.locateFile('images/sample.json'),'image')
      self.assertTrue('hat' in graph.get_nodes())
      self.assertTrue(graph.G.graph['idcount'] == graph.idc)
      self.assertTrue(graph.G.graph['projecttype'] == 'image')
      self.assertTrue(graph.idc > 1)

   def test_subgraph(self):
       initial = image_graph.createGraph(self.locateFile('images/sample.json'),'image')
       graph = initial.subgraph(['sample','orig_input','input_mod_1'])
       self.assertEqual(3,len(graph.get_nodes()))
       self.assertEqual(2,len(graph.get_edges()))

   def test_build_graph(self):
        edgePaths = ['videomasks', 'videosegment']
        value = {'videomasks': [
           {'endframe': 180, 'frames': 111, 'starttime': 2302.3, 'videosegment': u'videoSample5_videoSample6_mask_2302.3.hdf5', 'startframe': 69, 'endtime': 6006.0}, \
           {'endframe': 249, 'frames': 1, 'starttime': 8274.933333333334, 'videosegment': u'videoSample5_videoSample6_mask_8274.93333333.hdf5', 'startframe': 248, 'endtime': 8308.3}, \
           {'endframe': 283, 'frames': 1, 'starttime': 9409.4, 'videosegment': u'videoSample5_videoSample6_mask_9409.4.hdf5', 'startframe': 282, 'endtime': 9442.766666666666}, \
           {'endframe': 313, 'frames': 1, 'starttime': 10410.4, 'videosegment': u'videoSample5_videoSample6_mask_10410.4.hdf5', 'startframe': 312, 'endtime': 10443.766666666666}, \
           {'endframe': 326, 'frames': 1, 'starttime': 10844.166666666666, 'videosegment': u'videoSample5_videoSample6_mask_10844.1666667.hdf5', 'startframe': 325, 'endtime': 10877.533333333333}, \
           {'endframe': 352, 'frames': 2, 'starttime': 11678.333333333334, 'videosegment': u'videoSample5_videoSample6_mask_11678.3333333.hdf5', 'startframe': 350,'endtime': 11745.066666666668}]}
        result = image_graph.buildPath(value, edgePaths)
        self.assertEqual(len(result),6)
        self.assertEqual(result[0],'videomasks[0].videosegment')

   def test_attribute_replace(self):
       if os.path.exists('test_image_graph'):
           shutil.rmtree('test_image_graph')
       os.mkdir('test_image_graph')
       shutil.copy(self.locateFile('images/sample.jpg'),'test_image_graph/foo.jpg')
       shutil.copy(self.locateFile('images/sample.jpg'), 'test_image_graph/bar.jpg')
       graph = image_graph.createGraph('test_image_graph/foo.json', 'image',)
       graph.add_node('test_image_graph/foo.jpg',xxx=1)
       graph.add_node('test_image_graph/bar.jpg', xxx=1)
       nodes=  graph.get_nodes()
       graph.setDataItem('xxx',1)
       graph.setDataItem('projectfile',self.locateFile('tests/data/camera_sizes.json'))
       self.assertTrue(os.path.exists(os.path.join('test_image_graph','camera_sizes.json')))
       graph.add_edge(nodes[0],nodes[1], xxx=1)
       graph.replace_attribute_value('xxx',1,2)
       self.assertEquals(graph.getDataItem('xxx'),2)

       shutil.rmtree('test_image_graph')

if __name__ == '__main__':
    unittest.main()
