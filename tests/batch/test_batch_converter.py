# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from tests.test_support import TestSupport
from maskgen.scenario_model import ImageProjectModel
from maskgen.batch.batch_journal_conversion import BatchConverter
from maskgen.batch.batch_project import BatchProject


class TestBatchConverter(TestSupport):
    def test_converter(self):
        model = ImageProjectModel(self.locateFile('images/sample.json'))
        converter = BatchConverter(model)
        batch = converter.convert()
        bp = BatchProject(batch)
        bp.saveGraphImage('.')
