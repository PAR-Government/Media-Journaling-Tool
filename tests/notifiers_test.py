# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
from test_support import TestSupport
import unittest
from maskgen.scenario_model import ImageProjectModel
from maskgen.notifiers import NotifyDelegate
from maskgen.services.probes import ProbeSetBuilder, ProbeGenerator, EmptyCompositeBuilder
import logging


class TestNotifiers(TestSupport):

   def test_memory(self):
       model = ImageProjectModel(self.locateFile('images/sample.json'),
                                 notify=NotifyDelegate([]))
       ProbeGenerator(scModel=model, processors=[ProbeSetBuilder(scModel=model, compositeBuilders=[EmptyCompositeBuilder])])()
       key1 = ('composite', ('orig_input', 'input_mod_1'),  ('input_mod_1', 'input_mod_2'))
       key2 = ('composite', ('orig_input', 'input_mod_1'),  ('input_mod_2', 'input_mod_2_3'))
       key3 = ('composite', ('orig_input', 'input_mod_1'),  ('input_mod_2_3', 'input_mod_2_47'))
       key4 = ('donor', ('hat_splice_crop', 'input_mod_1'), ('hat', 'hat_splice'))
       memory = model.get_probe_mask_memory()
       self.assertTrue (memory[key1] is not None)
       self.assertTrue (memory[key2] is not None)
       self.assertTrue (memory[key3] is not None)
       self.assertTrue (memory[key4] is not None)
       model.select(('input_mod_2','input_mod_2_3'))
       model.update_edge( model.getDescription())
       self.assertTrue (memory[key1] is not None)
       self.assertTrue (memory[key2] is None)
       self.assertTrue (memory[key3] is None)
       self.assertTrue (memory[key4] is not None)
       model.select(('hat_splice', 'hat_splice_rot_1'))
       model.update_edge(model.getDescription())
       self.assertTrue (memory[key1] is not None)
       self.assertTrue (memory[key2] is None)
       self.assertTrue (memory[key3] is None)
       self.assertTrue (memory[key4] is None)




