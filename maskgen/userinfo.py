# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
"""
   Support UID discovery using a class that supports a method getpwuid().
   tool_set.setPwdX(classInstance) to set the class.  By default, the os UID is used.
"""
import getpass
import config

try:
    import pwd
    import os

    class PwdX():
        def getpwuid(self):
            return pwd.getpwuid(os.getuid())[0]

except ImportError:

    class PwdX():
        def getpwuid(self):
            return getpass.getuser()

class CustomPwdX:
    uid = None

    def __init__(self, uid):
        self.uid = uid

    def getpwuid(self):
        return self.uid

def setPwdX(api):
    config.global_config['pwdAPI'] = api

def get_username():
    return config.global_config['pwdAPI'].getpwuid() if 'pwdAPI' in config.global_config else PwdX().getpwuid()