from __future__ import print_function
import sys
from maskgen.plugins import loadPlugins, callPlugin, getOperation
from maskgen.image_wrap import  openImageFile
from maskgen.tool_set import validateAndConvertTypedValue
from maskgen import software_loader



def run_plugin(argv=None):
    import argparse
    import itertools

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--plugin', help='name of plugin', required=True)
    parser.add_argument('--input', help='base image or video',required=True)
    parser.add_argument('--output', help='result image or video',  required=True)
    parser.add_argument('--arguments', nargs='+', default={},  help='Additional operation/plugin arguments e.g. rotation 60')
    args = parser.parse_args()

    op = software_loader.getOperation(getOperation(args.plugin)['name'])
    parsedArgs = dict(itertools.izip_longest(*[iter(args.arguments)] * 2, fillvalue=""))
    for key in parsedArgs:
        parsedArgs[key] = validateAndConvertTypedValue(key, parsedArgs[key], op,
                                                                skipFileValidation=False)

    loadPlugins()
    args, msg = callPlugin(args.plugin, openImageFile(args.input), args.input, args.output, **parsedArgs)
    if msg is not None:
        print (msg)
    if args is not None:
        print ('Results:')
        print (str(args))

if __name__ == "__main__":
    sys.exit(run_plugin())