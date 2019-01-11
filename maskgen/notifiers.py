# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================
from os import remove
from tool_set import compose_overlay_name
from pkg_resources import iter_entry_points
import qa_logic

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
    def __init__(self, notifiers):
        self.notifiers = notifiers

    def __call__(self,*args,**kwargs):
        ok = True
        for notify in self.notifiers:
            ok &= notify(*args,**kwargs)
        return ok

    def get_notifier_by_type(self, notifier_type):
        return next((notifier for notifier in self.notifiers if isinstance(notifier, notifier_type)), None)

    def replace(self, notifier):
        try:
            index = self.notifiers.index(notifier)
            self.notifiers[index] = notifier
        except ValueError:
            self.notifiers.append(notifier)

class ValidationNotifier:
    def __init__(self, total_errors=None):
        self.total_errors = total_errors

    def __eq__(self, other):
        return other.__class__ == self.__class__

    def __call__(self, *args, **kwargs):
        if args[1] in ['label', 'export']:
            return True
        else:
            self.total_errors = None
            return True

class QaNotifier:
    def __init__(self, scmodel):
        """

        :param scmodel:
        @type scmodel: ImageProjectModel
        """
        self.qadata = None
        self.scmodel = scmodel
        self.scmodel.set_probe_mask_memory(ProbeMaskMemory())

    def __call__(self, *args, **kwargs):
        if args[1] != 'update_edge':
            return True
        else:
            scmodel = self.scmodel
            mem = self.scmodel.get_probe_mask_memory()
            qadata = qa_logic.ValidationData(scmodel)
            # select edge in Model
            scmodel.select(args[0])
            modified_edge = scmodel.getDescription()
            edback, backs = self._backtrack(modified_edge)
            critlinks = qadata.keys()
            critdict = self._dictionaryify(qadata.keys())
            for i in backs:
                curl = critdict[i] if i in critdict else []
                for fin in curl:
                    link = '->'.join([i,fin])
                    if link in critlinks:
                        qadata.set_qalink_status(link,'no')
                        qadata.set_qalink_designation(link, "")
                        try:
                            remove(compose_overlay_name(target_file= self.scmodel.G.get_pathname(args[0][1]), link=link))
                        except OSError:
                            pass

            edfwd, fwd = self._forwards(modified_edge)
            for i in fwd:
                curl = critdict[i] if i in critdict else []
                for fin in curl:
                    donor = '<-'.join([i,fin])
                    if donor in critlinks:
                        qadata.set_qalink_status(donor,'no')
                        qadata.set_qalink_designation(donor, "")
                        try:
                            remove(compose_overlay_name(target_file= self.scmodel.G.get_pathname(args[0][1]), link=donor))
                        except OSError:
                            pass

            for back in edback:
                # all predecessor edges flow through forward
                mem.forget(back, 'composite', edfwd)

            for forward in edfwd:
                # all successor edges flow through backward
                mem.forget(forward, 'donor', edback)

            return True

    def _dictionaryify(self,l):
        d = {}
        for k in l:
            tup = tuple(k.split("->")) if len(k.split('->'))>1 else tuple(k.split('<-'))
            if tup[0] in d:
                d[tup[0]].append(tup[1])
            else:
                d[tup[0]] = [tup[1]]
        return d

    #This needs to be changed do it by hand
    def _forwards(self, n):
        fo = [n.end]
        fwdedges = [(n.start,n.end)]
        condition = lambda x, y: True
        paths_tuples = self.scmodel.findPaths(n.end, condition)
        for path_tuple in paths_tuples:
            path = path_tuple[0][:-1]
            path.reverse()
            prev = n.end
            for path_part in path:
               fwdedges.append((prev,path_part))
               fo.append(path_part)
               prev = path_part
        return fwdedges, fo

    def _backtrack(self, n):
        back = [n.end]
        backedge = [(n.start,n.end)]
        back.append(self.scmodel.getFileName(n.end))
        g = self.scmodel.getGraph()
        cur = self.scmodel.getDescriptionForPredecessor(n.start)
        seen = []
        next = [n.end]
        while len(next) != 0:
            cur = next.pop(0)
            if cur not in seen:
                prevs = g.predecessors(cur)
                for p in prevs:
                    backedge.append((p,cur))
                back.append((self.scmodel.getFileName(cur)))
                next.extend(prevs)
        return backedge, back

class ProbeMaskMemory:
    def __init__(self):
        self.baseTypeEdge={}

    def __getitem__(self, item):
        if len(item) == 3:
            if item[0] == 'composite' or item[0] == 'donor':
                basedic = self.baseTypeEdge[item[1]] if item[1] in self.baseTypeEdge else None
                edgedic = basedic[item[0]] if basedic is not None and item[0] in basedic else None
                value = edgedic[item[2]] if edgedic is not None and item[2] in edgedic else None
                return value
        elif len(item) == 2:
            if item[0] == 'composite' or item[0] == 'donor':
                basedic = self.baseTypeEdge[item[1]] if item[1] in self.baseTypeEdge else None
                edgedic = basedic[item[0]] if basedic is not None and item[0] in  basedic else None
                return edgedic
        else:
            if item[0] == 'composite' or item[0] == 'donor':
                basedic = self.baseTypeEdge[item[0]] if item[0] in self.baseTypeEdge else None
                return basedic

    def __setitem__(self, key, item):
        if key[0] == 'composite' or key[0] == 'donor':
            if key[1] not in self.baseTypeEdge:
                self.baseTypeEdge[key[1]] = {}
            if key[0] not in self.baseTypeEdge[key[1]]:
                self.baseTypeEdge[key[1]][key[0]] = {}
            self.baseTypeEdge[key[1]][key[0]][key[2]] = item

    def forget(self, base, probe_type, references=None):
        if base in self.baseTypeEdge and probe_type in self.baseTypeEdge[base]:
            for edge in references if references is not None else []:
                try:
                    self.baseTypeEdge[base][probe_type].pop(edge)
                except:
                    pass
