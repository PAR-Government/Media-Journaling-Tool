import csv
import unittest


import numpy as np
from maskgen.services.probes import ProbeGenerator, ProbeSetBuilder, CompositeExtender, \
    DetermineTaskDesignation,ExtendProbesForDetectEdges, fetch_qaData_designation
from maskgen.graph_rules import processProjectProperties
from maskgen.mask_rules import Jpeg2000CompositeBuilder,ColorCompositeBuilder
from maskgen.scenario_model import ImageProjectModel
from maskgen.software_loader import getOperation
from maskgen.support import getPathValuesFunc
from mock import patch, Mock
from test_support import TestSupport

def compose_segment_mask(name, length, start_frame, rate, corner):
    from maskgen.tool_set import GrayBlockWriter
    w = GrayBlockWriter(name, rate)
    start_time = (start_frame - 1) * 1000.0 / rate
    i = 0
    while i < length:
        mask = np.ones((512, 512)).astype('uint8') * 255
        mask[corner[0]:corner[0] + 64, corner[1]:corner[1] + 64] = np.random.randint(0, 2, (64, 64),
                                                                                     dtype='uint8') * 255
        w.write(mask, start_time + (i * 1000.0 / rate), start_frame + i)
        i += 1
    w.close()
    return w.filename

from maskgen.video_tools import create_segment


class test_get_frame_count_callable:
    def __call__(self, *args, **kwargs):
        return test_get_frame_count(args[0])


class test_get_shape_callable:
    def __call__(self, *args, **kwargs):
        return (512,512)

def test_get_frame_count(thing):
    if thing in ['./f1', './f3']:
        return create_segment(starttime=0, startframe=1, endtime=4300, endframe=42, type='video', frames=43, rate=10)
    else:
        return create_segment(starttime=0, startframe=1, endtime=4400, endframe=43, type='video', frames=44, rate=10)


class TestToolSet(TestSupport):
    def test_hdf5_composite(self):
        from maskgen.tool_set import GrayBlockReader
        from maskgen.mask_rules import Probe, HDF5CompositeBuilder, segmentToVideoSegment

        probe1 = Probe(('a', 'b'), 'f1', 'b1', None, finalImageFileName='f1', targetVideoSegments=[
            segmentToVideoSegment(create_segment(starttime=1000, startframe=11, endtime=1900, endframe=20, type='video', frames=10,
                           rate=10,
                           videosegment=compose_segment_mask('ab1', 10, 11, 10,
                                                             (64, 64)))),
            segmentToVideoSegment(create_segment(starttime=3000, startframe=31, endtime=3900, endframe=40, type='video', frames=10, rate=10,
                           videosegment=compose_segment_mask('ab2', 10, 31, 10,
                                                             (64, 64))))
        ])
        probe2 = Probe(('a', 'b'), 'f2', 'b1', None, finalImageFileName='f2',
                       targetVideoSegments=probe1.targetVideoSegments)
        probe3 = Probe(('a', 'b'), 'f3', 'b1', None, finalImageFileName='f3', targetVideoSegments=[
            segmentToVideoSegment(create_segment(starttime=1000, startframe=11, endtime=1900, endframe=20, type='video', frames=10,
                           rate=10,
                           videosegment=compose_segment_mask('ab3', 10, 11, 10,
                                                             (256, 256)))),
                                  segmentToVideoSegment(create_segment(starttime=3000, startframe=31, endtime=3900, endframe=40, type='video', frames=10, rate=10,
                           videosegment=compose_segment_mask('ab4', 10, 31, 10,
                                                             (256, 256))))
        ])
        probes = [probe1, probe2, probe3]
        builder = HDF5CompositeBuilder()
        graph = Mock()
        graph.dir = '.'
        with patch('maskgen.video_tools.get_frame_count',
                   new_callable=test_get_frame_count_callable):
            with patch('maskgen.video_tools.get_shape_of_video',
                       new_callable=test_get_shape_callable):
               builder.initialize(graph, probes)
        results = builder.finalize(probes)
        self.assertEqual(1, probe1.composites['hdf5']['bit number'])
        self.assertEqual(1, probe2.composites['hdf5']['bit number'])
        self.assertEqual(2, probe3.composites['hdf5']['bit number'])
        first = results[(10, 43, 4300, 512, 512)]
        second = results[(10, 44, 4400, 512, 512)]
        self.assertNotEquals(first, second)
        r = GrayBlockReader(first, start_frame=11, start_time=1000)
        m = r.read()[:,:,0]
        self.assertTrue(np.all(m[0:64, 0:64] == 0))
        self.assertTrue(np.sum(m[64:128, 64:128] / 2) == 0)
        self.assertTrue(np.sum(m[64:128, 64:128] % 2) > 0)
        self.assertTrue(np.sum(m[256:310, 256:310] / 2) > 0)
        self.assertTrue(np.sum(m[256:310, 256:310] % 2) == 0)
        r = GrayBlockReader(second, start_frame=11, start_time=1000)
        m = r.read()[:,:,0]
        self.assertTrue(np.all(m[0:64, 0:64] == 0))
        self.assertTrue(np.sum(m[64:128, 64:128] / 2) == 0)
        self.assertTrue(np.sum(m[64:128, 64:128] % 2) > 0)
        self.assertTrue(np.sum(m[256:310, 256:310] / 2) == 0)
        self.assertTrue(np.sum(m[256:310, 256:310] % 2) == 0)

        r = GrayBlockReader(first, start_frame=31, start_time=3000)
        m = r.read()[:,:,0]
        self.assertTrue(np.all(m[0:64, 0:64] == 0))
        self.assertTrue(np.sum(m[64:128, 64:128] / 2) == 0)
        self.assertTrue(np.sum(m[64:128, 64:128] % 2) > 0)
        self.assertTrue(np.sum(m[256:310, 256:310] / 2) > 0)
        self.assertTrue(np.sum(m[256:310, 256:310] % 2) == 0)
        r = GrayBlockReader(second, start_frame=31, start_time=3000)
        m = r.read()[:,:,0]
        self.assertTrue(np.all(m[0:64, 0:64] == 0))
        self.assertTrue(np.sum(m[64:128, 64:128] / 2) == 0)
        self.assertTrue(np.sum(m[64:128, 64:128] % 2) > 0)
        self.assertTrue(np.sum(m[256:310, 256:310] / 2) == 0)
        self.assertTrue(np.sum(m[256:310, 256:310] % 2) == 0)

    def test_composite(self):
        scModel = ImageProjectModel(self.locateFile('images/sample.json'))
        processProjectProperties(scModel)
        scModel.assignColors()
        generator = ProbeGenerator(scModel=scModel, processors=[ProbeSetBuilder(scModel=scModel,
                                                                                compositeBuilders=[Jpeg2000CompositeBuilder,
                                                                                               ColorCompositeBuilder]),
                                                                DetermineTaskDesignation(scModel, inputFunction=fetch_qaData_designation)])
        probeSet = generator()
        self.assertTrue(len(probeSet) == 2)
        self.assertTrue(len([x for x in probeSet if x.edgeId == ('input_mod_2','input_mod_2_3')]) == 1)
        scModel.toCSV('test_composite.csv',additionalpaths=[getPathValuesFunc('linkcolor'), 'basenode'])
        self.addFileToRemove('test_composite.csv')
        with open('test_composite.csv','rb') as fp:
            reader = csv.reader(fp)
            for row in reader:
                self.assertEqual(6, len(row))
                self.assertTrue(getOperation(row[3]) is not None)
        self.assertTrue(len(probeSet) == 2)
        self.assertTrue('jp2' in probeSet[0].composites)
        self.assertTrue('color' in probeSet[0].composites)
        self.assertTrue('bit number' in probeSet[0].composites['jp2'])
        self.assertTrue('file name' in probeSet[0].composites['jp2'])
        self.assertTrue('color' in probeSet[0].composites['color'])
        self.assertTrue('file name' in probeSet[0].composites['color'])
        self.assertTrue('spatial' in probeSet[0].taskDesignation)

        full_set = ExtendProbesForDetectEdges(scModel, lambda x: True).apply(probeSet)
        self.assertTrue(len(full_set) == 6)
        for i in range(2,6):
            self.assertEqual('detect',full_set[i].taskDesignation)



    def test_composite_extension(self):
        model = ImageProjectModel(self.locateFile('images/sample.json'))
        model.assignColors()
        model.selectEdge('input_mod_1', 'input_mod_2')
        prior_probes = CompositeExtender(model).constructPathProbes(start='input_mod_1')
        prior_composite = prior_probes[-1].composites['color']['image']
        new_probes = CompositeExtender(model).extendCompositeByOne(prior_probes)
        composite = new_probes[-1].composites['color']['image']
        self.assertTrue(sum(sum(np.all(prior_composite.image_array != [255, 255, 255], axis=2))) -
                        sum(sum(np.all(composite.image_array != [255, 255, 255], axis=2))) < 100)

if __name__ == '__main__':
    unittest.main()
