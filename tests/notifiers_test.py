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
from maskgen.notifiers import QaNotifier,NotifyDelegate

class TestNotifiers(TestSupport):

   def test_memory(self):
       model = ImageProjectModel(self.locateFile('images/sample.json'),notify=NotifyDelegate([]))
       model.getProbeSetWithoutComposites()
       key1 = ('composite', ('orig_input', 'input_mod_1'),  ('input_mod_1', 'input_mod_2'))
       key2 = ('composite', ('orig_input', 'input_mod_1'),  ('input_mod_2', 'input_mod_2_3'))
       key3 = ('composite', ('orig_input', 'input_mod_1'),  ('input_mod_2_3', 'input_mod_2_47'))
       key4 = ('donor', ('orig_input', 'input_mod_1'), ('hat', 'hat_splice'))
       key5 = ('donor', ('orig_input', 'input_mod_1'), ('hat_splice_rot_1', 'hat_splice_crop'))
       qanotifier = model.notify
       memory = model.get_probe_mask_memory()
       self.assertTrue (memory[key1] is not None)
       self.assertTrue (memory[key2] is not None)
       self.assertTrue (memory[key3] is not None)
       self.assertTrue (memory[key4] is not None)
       self.assertTrue (memory[key5] is not None)
       model.select(('input_mod_2','input_mod_2_3'))
       model.update_edge( model.getDescription())
       self.assertTrue (memory[key1] is not None)
       self.assertTrue (memory[key2] is None)
       self.assertTrue (memory[key3] is None)
       self.assertTrue (memory[key4] is not None)
       self.assertTrue (memory[key5] is not None)
       model.select(('hat_splice', 'hat_splice_rot_1'))
       model.update_edge(model.getDescription())
       self.assertTrue (memory[key1] is not None)
       self.assertTrue (memory[key2] is None)
       self.assertTrue (memory[key3] is None)
       self.assertTrue (memory[key4] is None)
       self.assertTrue (memory[key5] is not None)




