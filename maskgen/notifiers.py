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
        self.notifiers = notifiers

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
                errors.append()
        if len(errors) > 0:
            return str(errors)


def getNotifier(loader):
    """
    Get notifiers attached to entry point maskgen_notifiers
    :param loader:
    :return:
    @type loader: MaskGenLoader
    """
    return CompositeMaskgenNotifer([entry_point.load()(loader) for entry_point in iter_entry_points(group='maskgen_notifiers', name=None)])
