# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
from maskgen.userinfo import setPwdX,CustomPwdX
from maskgen.validation.core import setValidators
from maskgen.validation.browser_api import ValidationBrowserAPI
from maskgen.validation.code_name_s3_api import ValidationCodeNameS3
from maskgen.plugins import loadPlugins
import logging

def initial_user(preferences,username=None):
    """
    Set the global user name for Maskgen services.  Defaults to the op-sys username if preferences
    or override kwargs is not provided.
    :param preferences:  default username if provided in preferences
    :param username:  optional override
    :return:
    """
    if username is not None:
        setPwdX(CustomPwdX(username))
    elif preferences.get_key('username') is not None:
        setPwdX(CustomPwdX(preferences.get_key('username')))
    else:
        logging.getLogger('maskgen').warn("Name not configured in preferences; using operating system user name")

def initialize_validators(preferences,validators=[]):
    """
    :param preferences:
    :param validators: list of class(ValidationAPI)
    :return:
    @type validators: list of class(ValidationAPI)
    """
    setValidators(preferences,validators)


def initialize(preferences, username=None, validators=None):
    """
    :param username: optional overriding username.
    :param validators: class extending ValidationAPI
    :return:
    @type validators: list of class(ValidationAPI)
    """
    initial_user(preferences,username=username)
    initialize_validators(preferences,
                          validators=validators if validators is not None else [ValidationBrowserAPI,ValidationCodeNameS3])
    loadPlugins()

