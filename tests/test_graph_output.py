import os
import numpy as np
from mock import Mock

from maskgen import graph_output
from maskgen.graph_output import GraphMediaHandler, UrlMediaFetcher, ExternalMediaHandler, FileMediaFetcher, \
    ImageGraphPainter
from maskgen.image_graph import createGraph
from maskgen.image_wrap import openImageFile, ImageWrapper
from maskgen.scenario_model import ImageProjectModel
from tests.test_support import TestSupport


class TestUrlHandler(TestSupport):

    def test_aproject(self):
        self.addFileToRemove('test_graph_output.png')
        scModel = ImageProjectModel(self.locateFile('images/sample.json'))
        graph_output.ImageGraphPainter(scModel.getGraph()).outputToFile('test_graph_output.png')
        self.assertTrue(os.path.exists('test_graph_output.png'))

    # def test_integration(self):
    #     self._test_with_external(UrlMediaFetcher())

    def test_local(self):
        def get_image(filename):
            return ImageWrapper(np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8))

        def get_url(filename):
            return './' + filename

        mock_fetcher = Mock(spec=UrlMediaFetcher())

        mock_fetcher.get_image = get_image
        mock_fetcher.get_url = get_url
        self._test_with_external(mock_fetcher)

    def _test_with_external(self, fetcher):
            handler = ExternalMediaHandler(fetcher)
            graph = createGraph(self.locateFile('data/ff0b47fa9f343b3bc5547e8f6b0b83ea.json'))

            im_orig = handler.get_image(graph, "ff0b47fa9f343b3bc5547e8f6b0b83ea")
            im_crop = handler.get_image(graph, "ff0b47fa9f343b3bc5547e8f6b0b83ea_crop")
            url_orig = handler.get_url(graph, "ff0b47fa9f343b3bc5547e8f6b0b83ea")
            url_crop = handler.get_url(graph, "ff0b47fa9f343b3bc5547e8f6b0b83ea_crop")

            self.assertEqual(im_orig[0].to_array().shape[:2], im_crop[0].to_array().shape[:2])

            print url_orig, url_crop

            painter = ImageGraphPainter(graph, handler)
            painter.output("test", formats=['.png', '.cmapx'])
            self.assertTrue(os.path.isfile('./test.png'))
            self.assertTrue(os.path.isfile('./test.cmapx'))

            # Clean up
            for node in graph.get_nodes():
                self.addFileToRemove(os.path.join(graph.dir, node + "_thb.png"))

            self.addFileToRemove("test.png")
            self.addFileToRemove("test.cmapx")

