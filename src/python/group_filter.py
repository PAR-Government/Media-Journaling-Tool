from maskgen_loader import MaskGenLoader

maskgenloader= MaskGenLoader()

class GroupFilter:
    name = None
    filters = []

    def __init__(self, name, filters):
      self.name = name
      self.filters = filters

class GroupFilterLoader:

   groups = {}

   def getGroups(self):
     return self.groups.values()

   def getGroup(self, name):
    return self.groups[name] if name in self.groups else None

   def getGroupNames(self):
     return self.groups.keys()

   def __init__(self):
     self.load()
   
   def load(self):
     global maskgenloader
     self.groups = {}
     newset = maskgenloader.get_key('filtergroups')
     if newset is not None:
       for k,v in newset.iteritems():
         self.groups[k]=GroupFilter(k,v)

   def add(self, groupfilter):
     self.groups[groupfilter.name] = groupfilter

   def remove(self, name):
     self.groups.pop(name)

   def save(self):
      global maskgenloader
      image = {}
      for k,v in self.groups.iteritems():
        image[k]=v.filters
      maskgenloader.save("filtergroups",image)


