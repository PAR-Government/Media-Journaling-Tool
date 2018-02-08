# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from pkg_resources import iter_entry_points
from maskgen.maskgen_loader import MaskGenLoader

class MaskgenNotifer:

    def update_journal_status(self, journalid, user, comment,typeofjournal):
        return True

    def get_properties(self):
        return {}

    def check_status(self):
        return None

class CompositeMaskgenNotifer(MaskgenNotifer):

    notifiers = []
    def __init__(self,notifiers):
        self.notifiers = [notifier for notifier in notifiers if notifier is not None]

    def update_journal_status(self, journalid, user, comment, typeofjournal):
        ok  = True
        for notifier in self.notifiers:
            ok &= notifier.update_journal_status(journalid,user, comment,typeofjournal)
        return ok

    def get_properties(self):
        r = {}
        for notifier in self.notifiers:
            for k,v, in notifier.get_properties().iteritems():
                r[k] = v
        return r

    def check_status(self):
        errors = []
        for notifier in self.notifiers:
            error = notifier.check_status()
            if error is not None:
                errors.append(error)
        if len(errors) > 0:
            return str(errors)


def getNotifier(loader):
    import logging
    """
    Get notifiers attached to entry point maskgen_notifiers
    :param loader:
    :return:
    @type loader: MaskGenLoader
    """
    def loadEntryPoint(entry_point, loader):
        try:
            p = entry_point.load()(loader)
            logging.getLogger('maskgen').info('loaded ' +str(entry_point))
            return p
        except Exception as e:
            logging.getLogger('maskgen').error('Cannot load ' + str(entry_point) + ': ' + str(e))

    return CompositeMaskgenNotifer([loadEntryPoint(entry_point,loader) for entry_point in iter_entry_points(group='maskgen_notifiers', name=None)])
