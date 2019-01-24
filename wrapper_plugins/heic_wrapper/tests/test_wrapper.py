from heic_wrapper import opener
from unittest import TestCase
import os

class TestToolSet(TestCase):
    test_input = os.path.join(os.getcwd(), "test.heic")
    def test_all(self):
        result = opener.open_heic(filename=self.test_input)
        TestCase.assertIsNotNone(self, result)
