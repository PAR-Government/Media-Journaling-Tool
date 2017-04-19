from pkg_resources import iter_entry_points
from maskgen.maskgen_loader import MaskGenLoader

class MaskgenNotifer:

    def update_journal_status(self, journalid, comment):
        pass

class CompositeMaskgenNotifer(MaskgenNotifer):

    notifiers = []
    def __init__(self,notifiers):
        self.notifiers = notifiers

    def update_journal_status(self, journalid, comment):
        for notifier in self.notifiers:
            notifier.update_journal_status(journalid,comment)

def loadNotifier(loader):
    """
    :param loader:
    :return:
    @type loader: MaskGenLoader
    """
    return CompositeMaskgenNotifer([entry_point.load()(loader) for entry_point in iter_entry_points(group='maskgen_notifiers', name=None)])
