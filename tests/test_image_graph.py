from maskgen import image_graph
import unittest

class TestImageGraph(unittest.TestCase):

   def test_filetype(self):
      graph = image_graph.createGraph('images/sample.json','image')
      self.assertTrue('hat' in graph.get_nodes())
      self.assertTrue(graph.G.graph['idcount'] == graph.idc)
      self.assertTrue(graph.G.graph['projecttype'] == 'image')
      self.assertTrue(graph.G.graph['igversion'] == '0.1')
      self.assertTrue(graph.idc > 1)
      graph = image_graph.createGraph('tests/video.json')
      self.assertTrue(graph.G.graph['projecttype'] == 'video')


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
