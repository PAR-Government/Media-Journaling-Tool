from pkg_resources import iter_entry_points
from maskgen.maskgen_loader import MaskGenLoader

class MaskgenNotifer:

    def update_journal_status(self, journalid, comment,typeofjournal):
        pass

    def get_properties(self):
        return {}

class CompositeMaskgenNotifer(MaskgenNotifer):

    notifiers = []
    def __init__(self,notifiers):
        self.notifiers = notifiers

    def update_journal_status(self, journalid, comment, typeofjournal):
        for notifier in self.notifiers:
            notifier.update_journal_status(journalid,comment,typeofjournal)

    def get_properties(self):
        r = {}
        for notifier in self.notifiers:
            for k,v, in notifier.get_properties().iteritems():
                r[k] = v
        return r

def loadNotifier(loader):
    """
    :param loader:
    :return:
    @type loader: MaskGenLoader
    """
    return CompositeMaskgenNotifer([entry_point.load()(loader) for entry_point in iter_entry_points(group='maskgen_notifiers', name=None)])
