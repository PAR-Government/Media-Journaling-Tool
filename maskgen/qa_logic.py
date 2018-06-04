import time

from maskgen.tool_set import get_username


class ValidationData:

    def __init__(self, scmodel,qaState=None,qaPerson=None,time=None,qaComment=None,qadata=None):
        self.scmodel = scmodel
        if qaState is not None:
            self.scmodel.setProjectData('validation', qaState, excludeUpdate=True)
        if qaPerson is not None:
            self.scmodel.setProjectData('validatedby', qaPerson, excludeUpdate=True)
        if qaComment is not None:
            self.scmodel.setProjectData('qacomment', qaComment.strip())
        if time is not None:
            self.scmodel.setProjectData('validationdate', time.strftime("%m/%d/%Y"), excludeUpdate=True)
            self.scmodel.setProjectData('validationtime', time.strftime("%H:%M:%S"), excludeUpdate=True)
        if qadata is not None:
            self.qaData = qadata
        else:
            self.qaData = self.scmodel.getProjectData('qadata')
            if self.qaData is None:
                self.qaData = {}
                self._qamodel_update()



    def update_All(self, qaState=None, qaPerson=None, qaComment=None, qaData=None):
        if qaState is not None:
            self.scmodel.setProjectData('validation', qaState, excludeUpdate=True)
        if qaPerson is not None:
            self.scmodel.setProjectData('validatedby', qaPerson, excludeUpdate=True)
        if qaComment is not None:
            self.scmodel.setProjectData('qacomment', qaComment.strip())
        if time is not None:
            self.scmodel.setProjectData('validationdate', time.strftime("%m/%d/%Y"), excludeUpdate=True)
            self.scmodel.setProjectData('validationtime', time.strftime("%H:%M:%S"), excludeUpdate=True)
        if qaData is not None:
            self.scmodel.setProjectData('qadata', self.qaData)
            self.qaData = qaData

    def set_state(self, state):
        self.scmodel.setProjectData('validation', state, excludeUpdate=True)

    def set_qaPerson(self, qp):
        self.scmodel.setProjectData('validatedby', qp, excludeUpdate=True)

    def set_qaComment(self, qc):
        self.scmodel.setProjectData('qacomment', qc.strip())

    def set_qaData(self):
        self.scmodel.setProjectData('validationdate', time.strftime("%m/%d/%Y"), excludeUpdate=True)
        self.scmodel.setProjectData('validationtime', time.strftime("%H:%M:%S"), excludeUpdate=True)

    def set_qalink_status(self, t, s):
        if t not in self.qaData:
            self.qaData[t] = {}
        self.qaData[t]['done'] = s
        self._qamodel_update()

    def set_qalink_caption(self, t, s):
        if t not in self.qaData:
            self.qaData[t] = {}
        self.qaData[t]['caption'] = s
        self._qamodel_update()

    def get_state(self):
        return self.scmodel.getProjectData('validation',default_value='no')

    def get_qaPerson(self):
        return self.scmodel.getProjectData('validatedby')

    def get_qaComment(self):
        return self.scmodel.getProjectData('qacomment')

    def get_qaData(self):
        return self.scmodel.getProjectData('qadata')

    def get_qalink_status(self, t):
        if t not in self.qaData:
            self.qaData[t] = {}
        if 'done' not in self.qaData[t]:
            self.qaData[t]['done'] = 'no'
            self._qamodel_update()
        return self.qaData[t]['done']

    def get_qalink_caption(self, t):
        if t not in self.qaData:
            self.qaData[t] = {}
        if 'caption' not in self.qaData[t]:
            self.qaData[t]['caption'] = ""
            self._qamodel_update()
        return self.qaData[t]['caption']

    def keys(self):
        return self.qaData.keys()

    def _qamodel_update(self):
        self.scmodel.setProjectData('qadata', self.qaData)

    def clearProperties(self):
        validationProps = {'validation': 'no', 'validatedby': '', 'validationtime': '', 'validationdate': ''}
        currentProps = {}
        for p in validationProps:
            currentProps[p] = self.scmodel.getProjectData(p)
        datetimeval = time.clock()
        if currentProps['validationdate'] is not None and \
                len(currentProps['validationdate']) > 0:
            datetimestr = currentProps['validationdate'] + ' ' + currentProps['validationtime']
            datetimeval = time.strptime(datetimestr, "%m/%d/%Y %H:%M:%S")
        if all(vp in currentProps for vp in validationProps) and \
                currentProps['validatedby'] != get_username() and \
                self.scmodel.getGraph().getLastUpdateTime() > datetimeval:
            for key, val in validationProps.iteritems():
                self.scmodel.setProjectData(key, val, excludeUpdate=True)