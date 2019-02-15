import os
import shutil
import unittest
from hp.camera_handler import API_Camera_Handler
from hp.hp_data import process
from maskgen.maskgen_loader import MaskGenLoader
from mock import Mock
from hp import data_files


class TestHPTool(unittest.TestCase):
    def test_process_data(self):
        def get_key(key, *args, **kwargs):
            return 0 if key == "seq" else key
        self.settings = Mock()
        self.settings.get_key = get_key

        # Get a Camera (May be AS-ONE, May be sample, irrelevant for the test)
        cam = API_Camera_Handler(self, None, None, "sample", localfile=data_files._DEVICES)

        # Attempt to Process Data with it's Information
        current_dir = os.path.dirname(__file__)
        indir = os.path.join(current_dir, "test")
        odir = os.path.join(current_dir, "output")
        process(self, cam.get_all(), indir, odir)
        self.assertTrue(os.path.isdir(os.path.join(odir, "csv")) and os.listdir(os.path.join(odir, "csv")) != [])
        self.assertTrue(os.path.isdir(os.path.join(odir, "image")) and os.listdir(os.path.join(odir, "image")) != [])
        self.assertTrue(os.path.isdir(os.path.join(odir, "video")) and os.listdir(os.path.join(odir, "video")) != [])
        self.assertTrue(os.path.isdir(os.path.join(odir, "audio")) and os.listdir(os.path.join(odir, "audio")) != [])
        self.assertFalse(os.path.isdir(os.path.join(odir, "model")))
        shutil.rmtree(odir)

        # Attempt to Process 3D Models
        indir = os.path.join(current_dir, "test_model")
        process(self, {}, indir, odir)
        self.assertTrue(os.path.isdir(os.path.join(odir, "csv")) and os.listdir(os.path.join(odir, "csv")) != [])
        self.assertFalse(os.path.isdir(os.path.join(odir, "image")))
        self.assertFalse(os.path.isdir(os.path.join(odir, "video")))
        self.assertFalse(os.path.isdir(os.path.join(odir, "audio")))
        self.assertTrue(os.path.isdir(os.path.join(odir, "model")) and os.listdir(os.path.join(odir, "model")) != [])
        shutil.rmtree(odir)

    def tearDown(self):
        # If any of the tests fail, the output directory may have still been created
        if os.path.isdir(os.path.join(os.path.dirname(__file__), "output")):
            shutil.rmtree(os.path.join(os.path.dirname(__file__), "output"))
