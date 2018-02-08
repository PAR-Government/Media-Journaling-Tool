# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from maskgen import plugins, image_wrap

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--plugin', required=True, help='JSON File')
    parser.add_argument('--args', required=True, help='number of projects to build')
    args = parser.parse_args()
    arguments_list = args.args.split(',')
    arguments = {a.split(':')[0]: a.split(':')[1] for a in arguments_list}
    img = image_wrap.openImageFile(arguments['inputimage'])
    plugins.loadPlugins()
    plugins.callPlugin(args.plugin,img, arguments['inputimage'],arguments['outputimage'],**arguments)
if __name__ == '__main__':
    main()
