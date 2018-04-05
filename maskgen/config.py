# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
global_config = {}

def getAndSet(name, item):
    global global_config
    if name in global_config:
        return global_config[name]
    global_config[name] = item
    return item
