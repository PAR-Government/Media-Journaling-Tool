import maskgen
import os
import csv
import tempfile
from maskgen.scenario_model import loadProject, Probe
import json
import shutil
import sys
import copy
from maskgen.image_wrap import openImageFile, ImageWrapper
from maskgen.image_graph import extract_archive
from maskgen.batch import bulk_export
import unittest
import numpy as np
import logging
from maskgen.loghandling import set_logging


"""
A test system that will produce expected results if missing and checking expected results if available
"""

class TestMethod:

    def __init__(self,dir):
        self.resultsDir = dir
        self.probesData = dict()

    def loadProbesData(self):
        logging.getLogger('maskgen').info('Loading {}'.format(self.resultsDir))
        with open(os.path.join(self.resultsDir, 'probes.txt'), 'r') as f:
            self.probesData = json.load(f)

    def saveProbesData(self):
        logging.getLogger('maskgen').info('Saving {}'.format(self.resultsDir))
        with open(os.path.join(self.resultsDir, 'probes.txt'), 'w') as f:
            json.dump(self.probesData, f, indent=2, encoding='utf-8')

    def processProbe(self,probe):
        return []

    def probesMissed(self):
        return []

class SeedTestMethod(TestMethod):

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
        item = {}
        item['targetBaseNodeId'] = probe.targetBaseNodeId
        item['edgeId'] = probe.edgeId
        item['finalNodeId'] = probe.finalNodeId
        item['donorBaseNodeId'] = probe.donorBaseNodeId
        if probe.targetMaskFileName is not None:
            item['targetMaskFileName'] = os.path.split(probe.targetMaskFileName)[1]
            shutil.copy(probe.targetMaskFileName, os.path.join(self.resultsDir, os.path.split(probe.targetMaskFileName)[1]))
        if probe.donorMaskFileName is not None:
            shutil.copy(probe.donorMaskFileName, os.path.join(self.resultsDir, os.path.split(probe.donorMaskFileName)[1]))
            item['donorMaskFileName'] = os.path.split(probe.donorMaskFileName)[1]
        self.probesData[itemid] = item
        return []


def loadImage(filename):
    return openImageFile(filename)

def compareMask(got, expected):
    """

    :param got:
    :param expected:
    :return:
    @type got: ImageWrapper
    @type expected: ImageWrapper
    """
    if got is not None and expected is not None:
        diff = abs(got.image_array.astype('float')-expected.image_array.astype('float'))
        diffsize = np.sum(diff>0)
        masksize = np.sum(expected.image_array>0)
        if diffsize/masksize <= 0.05:
            return True
    return False

class RunTestMethod(TestMethod):


    def __init__(self, dir):
        TestMethod.__init__(self,dir)

    def loadProbesData(self):
        TestMethod.loadProbesData(self)
        self.notprocessed = copy.deepcopy(self.probesData)

    def saveProbesData(self):
        pass

    def processProbe(self, probe):
        """
        :param probe:
        :return:
        @type probe: Probe
        """
        itemid = probe.targetBaseNodeId + '_' + str(probe.edgeId) + '_' + probe.finalNodeId + '_' + str(probe.donorBaseNodeId)
        if itemid not in self.probesData:
            return ['Missing Probe']
        item =self.probesData[itemid]
        self.notprocessed.pop(itemid)
        errors = []
        if probe.targetMaskFileName is None and 'targetMaskFileName' in item:
            errors.append('Expected targetMaskFileName {}'.format(item['targetMaskFileName']))
        if probe.donorMaskFileName  is None and 'donorMaskFileName' in item:
            errors.append('Expected donorMaskFileName {}'.format(item['donorMaskFileName']))
        if probe.targetMaskFileName is not None and 'targetMaskFileName' not in item:
            errors.append('Got unexpected targetMaskFileName {}'.format(item['targetMaskFileName']))
        if probe.donorMaskFileName is not None and 'donorMaskFileName' not in item:
            errors.append('Got unexpected donorMaskFileName {}'.format(item['donorMaskFileName']))
        if probe.targetMaskFileName is not None and 'targetMaskFileName' in item:
            if not compareMask(probe.targetMaskImage, loadImage(os.path.join(self.resultsDir,item['targetMaskFileName']))):
                errors.append('Mask mismatch targetMaskFileName {}'.format(item['targetMaskFileName']))
        if probe.donorMaskFileName is not None and 'donorMaskFileName' in item:
            if not compareMask(probe.donorMaskImage, loadImage(os.path.join(self.resultsDir, item['donorMaskFileName']))):
                errors.append('Mask mismatch donorMaskFileName {}'.format(item['donorMaskFileName']))
        return errors

    def probesMissed(self):
        return [Probe(self.probesData[item]['edgeId'],
                      self.probesData[item]['finalNodeId'],
                      self.probesData[item]['targetBaseNodeId'],'','','',
                      self.probesData[item]['donorBaseNodeId'],None,None) for item in self.notprocessed]

def runIT(tmpFolder=None):

    if not os.path.exists('projects'):
        return

    files_to_process = []
    for item in os.listdir('projects'):
        if item.endswith('tgz'):
            files_to_process.append(os.path.abspath(os.path.join('projects',item)))

    doneFile = 'testsDone'
    skips = []
    if os.path.exists(doneFile):
        with open(doneFile, 'r') as skip:
            skips = skip.readlines()
        skips = [x.strip() for x in skips]

    count = 0
    errorCount = 0
    with open(doneFile, 'a') as done_file:
        with open(os.path.join('ErrorReport_' + str(os.getpid()) + '.csv'), 'w') as csvfile:
            error_writer = csv.writer(csvfile, delimiter = ' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            for file_to_process in files_to_process:
                hasError = False
                if file_to_process in skips:
                    count += 1
                    continue
                logging.getLogger('maskgen').info(file_to_process)
                dir = tempfile.mkdtemp(dir=tmpFolder) if tmpFolder else tempfile.mkdtemp()
                try:
                    extract_archive(file_to_process, dir)
                    for project in bulk_export.pick_projects(dir):
                        scModel = loadProject(project)
                        logging.getLogger('maskgen').info('Processing {} '.format(scModel.getName()))
                        resultsDir = os.path.abspath(os.path.join('expected', scModel.getName()))
                        method = None
                        if not os.path.exists(resultsDir):
                            os.mkdir(resultsDir)
                            method = SeedTestMethod(resultsDir)
                        else:
                            method = RunTestMethod(resultsDir)
                        method.loadProbesData()
                        probes = scModel.getProbeSet()
                        logging.getLogger('maskgen').info('Processing {} probes'.format(len(probes)))
                        for probe in probes:
                            for error in method.processProbe(probe):
                                errorCount+=1
                                hasError=True
                                error_writer.writerow((scModel.getName(), probe.targetBaseNodeId, probe.finalNodeId,
                                                      probe.edgeId, error))
                        method.saveProbesData()
                        for probe in method.probesMissed():
                            errorCount += 1
                            hasError=True
                            error_writer.writerow((scModel.getName(), probe.targetBaseNodeId, probe.finalNodeId,
                                                  probe.edgeId, "Missing"))
                        if not hasError:
                            done_file.write(file_to_process + '\n')
                            done_file.flush()
                        csvfile.flush()
                except Exception as e:
                    logging.getLogger('maskgen').error(str(e))
                    errorCount += 1
                sys.stdout.flush()
                count += 1
                shutil.rmtree(dir)
        if errorCount == 0:
            if os.path.exists(doneFile):
                os.remove(doneFile)
        return errorCount



class MaskGenITTest(unittest.TestCase):

    def setUp(self):
        set_logging()
        if not os.path.exists('expected'):
            os.mkdir('expected')

    def test_it(self):
        self.assertTrue(runIT() == 0)


if __name__ == '__main__':
    unittest.main()
