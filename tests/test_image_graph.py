from maskgen import image_graph
import unittest

class TestImageGraph(unittest.TestCase):

   def test_filetype(self):
      graph = image_graph.createGraph('images/sample.json','image')
      self.assertTrue('hat' in graph.get_nodes())
      self.assertTrue(graph.G.graph['idcount'] == graph.idc)
      self.assertTrue(graph.G.graph['projecttype'] == 'image')
      #self.assertTrue(graph.G.graph['igversion'] == '0.1')
      self.assertTrue(graph.idc > 1)
      graph = image_graph.createGraph('tests/video.json')
      self.assertTrue(graph.G.graph['projecttype'] == 'video')

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
       graph = image_graph.createGraph('images/sample.json', 'image')
       id1=  graph.add_node('foo.jpg',xxx=1)
       id2 = graph.add_node('bar.jpg', xxx=1)
       graph.setDataItem('xxx',1)
       graph.add_edge(id1,id2, xxx=1)
       graph.replace_attribute_value('xxx',1,2)
       self.assertEquals(graph.getDataItem('xxx'),2)

if __name__ == '__main__':
    unittest.main()
