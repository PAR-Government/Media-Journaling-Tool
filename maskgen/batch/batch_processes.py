# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from __future__ import print_function
import sys
import importlib

tools = {'extend': 'batch_process', 'create': 'batch_project', 'export': 'bulk_export',
         'convert': 'batch_journal_conversion', 'merge': 'batch_merge'}


def main():
    if len(sys.argv) == 1 or sys.argv[1] not in ['extend', 'create', 'export', 'convert', 'merge']:
        print('Invalid Tool.  Pick one of: ' + ', '.join(tools))
    else:
        module_name = tools[sys.argv[1]]
        module = importlib.import_module('maskgen.batch.' + module_name )
        print('Executing ' + module.__name__ + ' with ' + ', '.join(sys.argv[2:]))
        func = getattr(module, 'main')
        func(sys.argv[2:])


if __name__ == '__main__':
    main()

