# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

class IoCBroker:

   """
   @type components: dict[str,list of IoCComponent]
   @type providers: dict[str, list]
   """
   def __init__(self):
      self.components = {}
      self.providers = {}

   def define(self, requirement):
       """
       :param requirement:
       :return:
       @type requirement: IoCComponent
       """
       if requirement.name not in self.components:
           self.components[requirement.name] = []
       requirements = self.components[requirement.name]
       requirements.append(requirement)

   def register(self, name, provider):
       """

       :param provider:  some class
       :return:
       """
       if name not in self.components:
           raise KeyError, "Unknown service named %r" % name
       definition = self.components[name]
       for requirement in definition:
           if not requirement.assertion(provider):
               ValueError, "The value %r of %r does not match the specified criteria (%s)" \
               % (provider, name, str(requirement))
       self.providers[name] = provider

   def __getitem__(self, name):
        try:
             provider = self.providers[name]
        except KeyError:
             raise KeyError, "Unknown service named %r" % name
        return provider

broker = IoCBroker()

######################################################################
##
## Representation of Required Features and Feature Assertions
##
######################################################################

#
# Some basic requirements for service
#

def Attribute(name,att_type):
   def test(obj):
       if not hasattr(obj, name): return False
       return True
   return test

def Method(method):
   def test(obj):
         try:
            attr = getattr(obj, method)
         except AttributeError:
            return False
         if not callable(attr): return False
         return True
   return test

class IoCComponent(object):
   def __init__(self, name, feature):
      self.feature = feature.func_closure[0].cell_contents
      self.name = name
      self.assertion=feature
      broker.define(self)

   def __get__(self, obj, T):
      return getattr(self.result,self.feature)

   def __getattr__(self, name):
      assert name == 'result', "Unexpected attribute request other then 'result'"
      self.result = broker[self.name]
      return self.result



