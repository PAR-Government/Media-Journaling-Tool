import maskgen
import os
import csv
import tempfile
from maskgen.scenario_model import loadProject
from maskgen.services.probes import Probe, ProbeGenerator, ProbeSetBuilder, EmptyCompositeBuilder
import json
import shutil
import sys
import copy
from maskgen.image_wrap import ImageWrapper
from maskgen.tool_set import openImage
from maskgen.image_graph import extract_archive
from maskgen.batch import bulk_export
import unittest
import numpy as np
import logging
from maskgen.loghandling import set_logging
from maskgen.serialization.probes import deserialize_probe,serialize_probe, match_video_segments, compare_mask_images

"""
A test system that will produce expected results if missing and checking expected results if available.

"""

class TestMethod:

    """
    @type probes_data: dict of (str,Probe)
    """
    def __init__(self, results_dir='.'):
        self.results_dir = results_dir
        self.probes_data = dict()

    def loadProbesData(self):
        logging.getLogger('maskgen').info('Loading {}'.format(self.results_dir))
        with open(os.path.join(self.results_dir, 'probes.json'), 'r') as f:
            probesDict = json.load(f)
            for id, probe_data in probesDict.iteritems():
                self.probes_data[id] = deserialize_probe(probe_data, fileDirectory=self.results_dir)

    def saveProbesData(self):
        logging.getLogger('maskgen').info('Saving {}'.format(self.results_dir))
        with open(os.path.join(self.results_dir, 'probes.json'), 'w') as f:
            probesDict = dict()
            for id, probe in self.probes_data.iteritems():
                probesDict[id] = serialize_probe(probe, self.results_dir)
            json.dump(probesDict, f, indent=2, encoding='utf-8')

    def processProbe(self,probe):
        return []

    def probesMissed(self):
        return []

class SeedTestMethod(TestMethod):
    """
       Save expected results
    """

    def __init__(self, dir):
        TestMethod.__init__(self,dir)

    def loadProbesData(self):
        pass

    def processProbe(self,probe):
        """
        :param probe:
        :return:
        @type probe: Probe
        """
        itemid = probe.targetBaseNodeId + '_' +  str(probe.edgeId) + '_' + probe.finalNodeId + '_' + str(probe.donorBaseNodeId)
        self.probes_data[itemid] = probe
        return []


class RunTestMethod(TestMethod):
    """
    Run the test and compare results against expected
    """


    def __init__(self, dir):
        TestMethod.__init__(self,dir)

    def loadProbesData(self):
        TestMethod.loadProbesData(self)
        self.notprocessed = copy.deepcopy(self.probes_data)

    def saveProbesData(self):
        pass

    def processProbe(self, probe):
        """
        :param probe:
        :return:
        @type probe: Probe
        """
        expected_probe_id = probe.targetBaseNodeId + '_' + str(probe.edgeId) + '_' + probe.finalNodeId + '_' + str(probe.donorBaseNodeId)
        if expected_probe_id not in self.probes_data:
            return ['Missing Probe']
        expected_probe = self.probes_data[expected_probe_id]
        self.notprocessed.pop(expected_probe_id)
        errors = []

        if probe.targetMaskFileName is None:
            if expected_probe.targetMaskFileName is not None:
                errors.append('Expected targetMaskFileName {}'.format(expected_probe.targetMaskFileName))
        elif probe.targetMaskFileName is not None and expected_probe.targetMaskFileName  is None:
            errors.append('Got unexpected targetMaskFileName {}'.format(probe.targetMaskFileName))
        else:
            if not compare_mask_images(probe.targetMaskImage, openImage(os.path.join(self.results_dir, expected_probe.targetMaskFileName))):
                errors.append('Mask mismatch targetMaskFileName {}'.format(expected_probe.targetMaskFileName))

        if probe.donorMaskFileName is None:
            if expected_probe.donorMaskFileName is not None:
                errors.append('Expected donorMaskFileName {}'.format(expected_probe.donorMaskFileName))
        elif probe.donorMaskFileName is not None and expected_probe.donorMaskFileName is None:
            errors.append('Got unexpected donorMaskFileName {}'.format(probe.donorMaskFileName))
        else:
            if not compare_mask_images(probe.donorMaskImage, openImage(os.path.join(self.results_dir, expected_probe.donorMaskFileName))):
                errors.append('Mask mismatch donorMaskFileName {}'.format(expected_probe.donorMaskFileName))

        if not probe.targetVideoSegments and expected_probe.targetVideoSegments:
                errors.append('Missing target segments')
        elif expected_probe.targetVideoSegments and probe.targetVideoSegments:
            errors.extend(match_video_segments(expected_probe.targetVideoSegments, probe.targetVideoSegments))

        if not probe.donorVideoSegments and expected_probe.donorVideoSegments:
                errors.append('Missing donor segments')
        elif expected_probe.donorVideoSegments and probe.donorVideoSegments:
            errors.extend(match_video_segments(expected_probe.donorVideoSegments, probe.donorVideoSegments))

        return errors

    def probesMissed(self):
        return [Probe(self.probes_data[item].edgeId,
                      self.probes_data[item].finalNodeId,
                      self.probes_data[item].targetBaseNodeId, '', '', '',
                      self.probes_data[item].donorBaseNodeId, None, None) for item in self.notprocessed]

def run_it(temp_folder=None, expected_probes_directory='.', project_dir='projects'):
    """
    Store results in ErrorReport CSV file.
    If a new project is found in project_dir that has not been processed (not in expected_probes_directory), the results are stored in expected_probes_directory.
    If a project is found in expected_probes_directory, then the project is rerun to compoare to the expected results.
    :param temp_folder:  place to put exploded journals.  Removed upon completion
    :param expected_probes_directory: Expected probes store
    :param project_dir: projects to test
    :return:
    """
    from time import strftime
    if not os.path.exists(project_dir):
        return

    files_to_process = []
    for item in os.listdir(project_dir):
        if item.endswith('tgz'):
            files_to_process.append(os.path.abspath(os.path.join(project_dir,item)))

    done_file_name = os.path.join(expected_probes_directory, 'it_tests_done.txt')
    skips = []
    if os.path.exists(done_file_name):
        with open(done_file_name, 'r') as skip:
            skips = skip.readlines()
        skips = [x.strip() for x in skips]

    count = 0
    errorCount = 0
    with open(done_file_name, 'a') as done_file:
        with open(os.path.join(expected_probes_directory, 'ErrorReport_' + strftime('%b_%d_%Y_%H_%M_%S') + '.csv'), 'w') as csvfile:
            error_writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for file_to_process in files_to_process:
                is_error_found = False
                if file_to_process in skips:
                    count += 1
                    continue
                logging.getLogger('maskgen').info(file_to_process)
                process_dir = tempfile.mkdtemp(dir=temp_folder) if temp_folder else tempfile.mkdtemp()
                try:
                    extract_archive(file_to_process, process_dir)
                    for project in bulk_export.pick_projects(process_dir):
                        scModel = loadProject(project)
                        logging.getLogger('maskgen').info('Processing {} '.format(scModel.getName()))
                        expected_results_directory = os.path.abspath(os.path.join(expected_probes_directory, 'expected', scModel.getName()))
                        if not os.path.exists(expected_results_directory):
                            os.mkdir(expected_results_directory)
                            method = SeedTestMethod(expected_results_directory)
                        else:
                            method = RunTestMethod(expected_results_directory)
                        method.loadProbesData()
                        generator = ProbeGenerator(scModel=scModel, processors=[ProbeSetBuilder(scModel=scModel, compositeBuilders=[EmptyCompositeBuilder])])
                        probes = generator(keepFailures=True)
                        logging.getLogger('maskgen').info('Processing {} probes'.format(len(probes)))
                        for probe in probes:
                            for error in method.processProbe(probe):
                                errorCount+=1
                                is_error_found=True
                                error_writer.writerow((scModel.getName(), probe.targetBaseNodeId, probe.finalNodeId,
                                                      probe.edgeId, error))
                        method.saveProbesData()
                        for probe in method.probesMissed():
                            errorCount += 1
                            is_error_found=True
                            error_writer.writerow((scModel.getName(), probe.targetBaseNodeId, probe.finalNodeId,
                                                  probe.edgeId, "Missing"))
                        if not is_error_found:
                            done_file.write(file_to_process + '\n')
                            done_file.flush()
                        csvfile.flush()
                except Exception as e:
                    logging.getLogger('maskgen').error(str(e))
                    errorCount += 1
                sys.stdout.flush()
                count += 1
                shutil.rmtree(process_dir)
    if errorCount == 0:
        if os.path.exists(done_file_name):
            os.remove(done_file_name)
    return errorCount


class MaskGenITTest(unittest.TestCase):

    def setUp(self):
        from time import strftime
        set_logging(filename='maskgen_it'+ strftime('%b_%d_%Y_%H_%M_%S') + '.log')
        if not os.path.exists('it/expected'):
            os.makedirs('it/expected')

    def test_it(self):
        try:
            journalDir = os.environ['MASKGEN_TEST_FOLDER']
        except KeyError:
            journalDir = '../projects'

        self.assertTrue(run_it(expected_probes_directory='it', project_dir=journalDir) == 0)


if __name__ == '__main__':
    unittest.main()
