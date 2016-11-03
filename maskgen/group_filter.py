from maskgen_loader import MaskGenLoader
import plugins
from software_loader import getOperations, Operation, getOperation, getOperationsByCategory

maskgenloader= MaskGenLoader()

class GroupFilter:
    name = None
    filters = []

    def __init__(self, name, filters):
      self.name = name
      self.filters = filters

class GroupFilterLoader:

   groups = {}

   def getAvailableFilters(self,operations_used=list()):
       names = plugins.getOperationNames(noArgs=True)
       return [op_name for op_name in names if op_name not in operations_used]

   def getLoaderKey(self):
     return "filtergroups"

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
     plugins.loadPlugins()
     self.groups = {}
     newset = maskgenloader.get_key(self.getLoaderKey())
     if newset is not None:
       for k,v in newset.iteritems():
         self.groups[k]=GroupFilter(k,v)

   def add(self, groupfilter):
     self.groups[groupfilter.name] = groupfilter

   def remove(self, name):
     self.groups.pop(name)

   def getName(self):
       return "Filters"

   def save(self):
      global maskgenloader
      image = {}
      for k,v in self.groups.iteritems():
        image[k]=v.filters
      maskgenloader.save(self.getLoaderKey(),image)

def addToSet(aSet, aList):
    for item in aList:
        if item not in aSet:
            aSet.add(item)

def addToMap(to_map, from_map):
    for k,v in from_map.iteritems():
        to_map[k] = v

def get_transitions(filter):
    content = filter.filters
    if len(content) == 0:
        return []
    first_op = getOperation(content[0])
    second_op = getOperation(content[-1])
    transitions = []
    for first_op_trans in first_op.transitions:
        start = first_op_trans.split('.')[0]
        for second_op_trans in second_op.transitions:
             end = second_op_trans.split('.')[1]
             transition = start + '.' + end
             if transition not in transitions:
                 transitions.append(transition)
    return transitions

"""
Rules needed:
   Only one generateMask allowed
   Transitions must be checked to be valid
"""


class GroupOperationsLoader(GroupFilterLoader):

    def getLoaderKey(self):
        return "operationsgroups"

    def getName(self):
        return "Operations"

    def __init__(self):
        GroupFilterLoader.load(self)

    def getOperation(self, name):
        grp = self.getGroup(name)
        if grp is not None:
            includeInMask = False
            rules = set()
            opt_params = dict()
            mandatory_params = dict()
            analysisOperations = set()
            transitions = get_transitions(grp)
            generateMask = False
            grp_categories = set()
            for op in grp.filters:
                operation = getOperation(op)
                grp_categories.add(operation.category)
                includeInMask |= operation.includeInMask
                generateMask |= operation.generateMask
                addToSet(rules,operation.rules)
                addToMap(mandatory_params,operation.mandatoryparameters)
                addToMap(opt_params, operation.optionalparameters)
                addToSet(analysisOperations, operation.analysisOperations)
            opt_params = dict([(k, v) for (k, v) in opt_params.iteritems() if k is not mandatory_params])
            return Operation(name=name, category='Groups',
                             includeInMask=includeInMask,
                             generateMask=generateMask,
                             mandatoryparameters=mandatory_params,
                             description='User Defined',
                             optionalparameters=opt_params,
                             rules=list(rules),
                             transitions=transitions,
                             groupedOperations=grp.filters,
                             groupedCategories=grp_categories,
                             analysisOperations=analysisOperations)

        return None

    def getAvailableFilters(self, operations_used=list()):
        has_generate_mask = False
        for op_name in operations_used:
            real_op = getOperation(op_name, fake=True)
            has_generate_mask |= real_op.generateMask
        ops = getOperations()
        return [op_name for op_name in ops if op_name not in operations_used and not \
            (has_generate_mask and ops[op_name].generateMask)]

    def getCategoryForGroup(self, groupName):
        if groupName in self.getGroupNames():
            return "Groups"
        return None

    def getOperationsByCategory(self, startType, endType):
        cat = dict()
        cat['Groups'] = list()
        newset = maskgenloader.get_key(self.getLoaderKey())
        for group, content in newset.iteritems():
            if len(content) > 0:
                first_op = getOperation(content[0])
                for first_op_trans in first_op.transitions:
                    start = first_op_trans.split('.')[0]
                    if start != startType:
                        continue
                    second_op = getOperation(content[-1])
                    for second_op_trans in second_op.transitions:
                        end = second_op_trans.split('.')[1]
                        if end == endType:
                            cat['Groups'].append(group)
                            continue
        return cat


groupOpLoader = GroupOperationsLoader()

def getCategoryForOperation(name):
    global groupOpLoader
    ops = getOperations()
    if name in ops:
        return ops[name].category
    return groupOpLoader.getCategoryForGroup(name)

def getOperationWithGroups(name, fake=False):
    global groupOpLoader
    op = getOperation(name,fake=False)
    if op is None:
        op = groupOpLoader.getOperation(name)
    if op is None and fake:
        return getOperation(name,fake=True)
    return op

def getOperationsByCategoryWithGroups(sourcetype, targettype):
    global groupOpLoader
    res = dict(getOperationsByCategory(sourcetype, targettype))
    for k, v in groupOpLoader.getOperationsByCategory(sourcetype, targettype).iteritems():
        res[k] = v
    return res
