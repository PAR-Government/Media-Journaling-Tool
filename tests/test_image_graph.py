from maskgen import image_graph
import unittest

class TestImageGraph(unittest.TestCase):

   def test_filetype(self):
      graph = image_graph.createGraph('images/sample.json')
      self.assertFalse(isinstance(graph,image_graph.VideoGraph))
      self.assertTrue('hat' in graph.get_nodes())
      self.assertTrue(graph.G.graph['idcount'] == graph.idc)
      self.assertTrue(graph.G.graph['projecttype'] == 'image')
      self.assertTrue(graph.G.graph['igversion'] == '0.1')
      self.assertTrue(graph.idc > 1)
      graph = image_graph.createGraph('tests/video.json')
      self.assertTrue(isinstance(graph,image_graph.VideoGraph))

if __name__ == '__main__':
    unittest.main()
