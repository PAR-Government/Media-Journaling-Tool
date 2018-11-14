import os
import shutil
import unittest
import subprocess

from hp.camera_handler import API_Camera_Handler
from hp.hp_data import process
from maskgen.maskgen_loader import MaskGenLoader


class TestHPTool(unittest.TestCase):
    settings = MaskGenLoader()

    def test_process_data(self):
        # Get Camera
        browser_url = self.settings.get_key("apiurl")
        browser_token = self.settings.get_key("apitoken")
        cam = API_Camera_Handler(self, browser_url, browser_token, "AS-ONE")
        if len(cam.ids) != 1:
            self.fail("Unable to connect camera handler to browser.")

        # Attempt to Process Data with it's Information
        current_dir = os.path.split(__file__)[0]
        indir = os.path.join(current_dir, "test")
        outdir = os.path.join(current_dir, "output")
        process(self, cam.get_all(), indir, outdir)

        shutil.rmtree(outdir)

        indir = os.path.join(current_dir, "test_model")
        process(self, {}, indir, outdir)

        shutil.rmtree(outdir)


if __name__ == '__main__':
    unittest.main()
