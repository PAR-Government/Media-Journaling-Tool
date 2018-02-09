
class ValidationData:

    def __init__(self, scmodel,qaState=None,qaPerson=None,time=None,qaComment=None):
        self.scmodel = scmodel
        self.scmodel.setProjectData('validation', qaState, excludeUpdate=True)
        self.scmodel.setProjectData('validatedby', qaPerson, excludeUpdate=True)
        self.scmodel.setProjectData('validationdate', time.strftime("%m/%d/%Y"), excludeUpdate=True)
        self.scmodel.setProjectData('validationtime', time.strftime("%H:%M:%S"), excludeUpdate=True)
        self.scmodel.setProjectData('qacomment', qaComment.strip())

    def update_All(self,qaState=None,qaPerson=None,time=None,qaComment=None,qaData=None):
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
            self.qaData = qaData

    def set_state(self, state):
        self.scmodel.setProjectData('validation', state, excludeUpdate=True)
    def set_qaPerson(self, qp):
        self.scmodel.setProjectData('validatedby', qp, excludeUpdate=True)
    def set_qaComment(self, qc):
        self.scmodel.setProjectData('qacomment', qc.strip())
    def set_qaData(self, qd):
        self.scmodel.setProjectData('validationdate', excludeUpdate=True)
        self.scmodel.setProjectData('validationtime',  excludeUpdate=True)
    def get_state(self):
        return self.scmodel.getProjectData('validation', excludeUpdate=True)
    def get_qaPerson(self):
        return self.scmodel.getProjectData('validatedby', excludeUpdate=True)
    def get_qaComment(self):
        return self.scmodel.getProjectData('qacomment')
    def get_qaData(self):
        return self.qaData

