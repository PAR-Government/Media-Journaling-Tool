# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import argparse
import sys
import matplotlib
matplotlib.use("TkAgg")

def build_ui(argv):
    from maskgen.ui.masken_ui import runui
    runui(argv)

def main(argv=None):
    if (argv is None):
        argv = sys.argv
    if '--multiprocessing-fork' in sys.argv:
        return
    build_ui(argv)

if __name__ == "__main__":
    sys.exit(main())
