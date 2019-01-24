import json
import logging
from maskgen import ffmpeg_api
from maskgen.software_loader import getFileName
import re
from subprocess import Popen, PIPE
import sys

logger = logging.getLogger("maskgen")


class VersionChecker:
    def __init__(self):
        self.platform = "Windows" if sys.platform.startswith("win") else "Mac" if sys.platform == "darwin" else "Linux"
        version_file = getFileName("dependency_versions.json")
        if version_file is None:
            raise ValueError("dependency_versions.json was not found.")
        with open(version_file, "r") as f:
            self.versions = json.load(f)

    def check_tool(self, tool, found_version):
        if self.platform.lower() in self.versions and tool.lower() in self.versions[self.platform.lower()]:
            if found_version not in self.versions[self.platform.lower()][tool.lower()] and \
                    self.versions[self.platform.lower()][tool.lower()] != "*.*":
                return "{0} is not a supported version of {1} on {2}".format(found_version, tool, self.platform)
        return None

    def check_ffmpeg(self):
        return self.check_tool("FFmpeg", ffmpeg_api.get_ffmpeg_version())

    def check_opencv(self):
        import cv2
        return self.check_tool("OpenCV", cv2.__version__)

    def check_dot(self):
        p = Popen(["dot", "-V"], stdout=PIPE, stderr=PIPE)
        data = p.communicate()[1]
        if p.returncode == 0:
            v = re.findall("\d\.\d+\.\d", data)[0]
            return self.check_tool("Graphviz", v)
        else:
            return "Unable to check Graphviz version"
