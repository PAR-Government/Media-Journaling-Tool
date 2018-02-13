from pkg_resources import iter_entry_points
import qa_logic
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


class NotifyDelegate:
    def __init__(self, scmodel, notifiers):
        self.scmodel = scmodel
        self.notifiers = notifiers

    def __call__(self,*args,**kwargs):
        for notify in self.notifiers:
            notify(self.scmodel, args)

class QaNotifier:
    def __init__(self):
        self.qadata = None
    def __call__(self, scmodel, args, *kwargs):
        if args[1] != 'update_edge':
            pass
        else:
            self.scmodel = scmodel
            qadata = qa_logic.ValidationData(scmodel)
            edge = scmodel.select(args[0])
            cnode = scmodel.getDescription()
            backs = self._backtrack(cnode)

            critlinks = qadata.keys()
            critdict = self._dictionaryify(qadata.keys())
            for i in backs:
                curl = critdict[i] if i in critdict else []
                for fin in curl:
                    link = '->'.join([i,fin])
                    if link in critlinks:
                        qadata.set_qalink_status(link,'no')
            fwd = self._forwards(cnode)
            for i in fwd:
                curl = critdict[i] if i in critdict else []
                for fin in curl:
                    donor = '<-'.join([i,fin])
                    if donor in critlinks:
                        qadata.set_qalink_status(donor,'no')

    def _dictionaryify(self,l):
        d = {}
        for k in l:
            tup = tuple(k.split("->")) if len(k.split('->'))>1 else tuple(k.split('<-'))
            if tup[0] in d:
                d[tup[0]].append(tup[1])
            else:
                d[tup[0]] = [tup[1]]
        return d

    def _forwards(self, n):
        fo = []
        fo.append(self.scmodel.getFileName(n.end))
        curs = self.scmodel.G.successors(n.end)
        while curs != []:
            cur = curs.pop()
            for suc in self.scmodel.G.successors(cur):
                if suc not in fo:
                    curs.append(suc)
            #curs += self.scmodel.G.successors(cur)
            fo.append(self.scmodel.getFileName(cur))
        return fo

    def _backtrack(self, n):
        back = []
        back.append(self.scmodel.getFileName(n.end))
        cur = self.scmodel.getDescriptionForPredecessor(n.start)
        while cur is not None:
            back.append((self.scmodel.getFileName(cur.end)))
            cur = cur.start
            cur = self.scmodel.getDescriptionForPredecessor(cur)
        return back


