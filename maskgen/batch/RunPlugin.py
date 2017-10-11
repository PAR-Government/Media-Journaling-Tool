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
    plugins.runCustomPlugin(args.plugin,img, arguments['inputimage'],arguments['outputimage'],**arguments)
if __name__ == '__main__':
    main()
