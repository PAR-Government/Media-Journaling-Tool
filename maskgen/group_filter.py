# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from maskgen_loader import MaskGenLoader
import plugins
from software_loader import getOperations, Operation, getOperation, getOperationsByCategory, insertCustomRule, getRule,getFilters
import logging

maskgenloader = MaskGenLoader()

def addToSet(aSet, aList):
    if aList is None:
        return
    for item in aList:
        if item not in aSet:
            aSet.add(item)

def addToMap(to_map, from_map):
    if from_map is None:
        return
    for k, v in from_map.iteritems():
        to_map[k] = v


def get_transitions(operations):
    if len(operations) == 0:
        return []
    first_op = operations[0]
    second_op = operations[-1]
    transitions = []
    for first_op_trans in first_op.transitions:
        start = first_op_trans.split('.')[0]
        for second_op_trans in second_op.transitions:
            end = second_op_trans.split('.')[1]
            transition = start + '.' + end
            if transition not in transitions:
                transitions.append(transition)
    return transitions

def buildFilterOperation(pluginOp):
    import copy
    if pluginOp is None:
        return None
    realOp = getOperation(pluginOp['name'],fake=True)
    mandatory = copy.copy(realOp.mandatoryparameters)
    for k,v in  (pluginOp['arguments']  if 'arguments' in pluginOp and pluginOp['arguments'] is not None else {}).iteritems():
        mandatory[k] = v
    optional = {k:v for k,v in realOp.optionalparameters.iteritems() if k not in mandatory}
    logging.getLogger('maskgen').info('Build filter {}'.format(pluginOp['name']))
    return Operation(name=pluginOp['name'],
                     category=pluginOp['category'],
                     generateMask=realOp.generateMask,
                     mandatoryparameters=mandatory,
                     description=pluginOp['description'],
                     optionalparameters=optional,
                     rules=realOp.rules,
                     includeInMask=realOp.includeInMask,
                     transitions=pluginOp['transitions'],
                     parameter_dependencies=pluginOp['parameter_dependencies'] if 'parameter_dependencies' in pluginOp else None)

class GroupFilter:
    name = None
    filters = []

    def __init__(self, name, filters):
        self.name = name
        self.filters = filters
        self.operation = None

    def isValid(self):
        for filter in self.filters:
            if plugins.getOperation(filter) is None:
                logging.getLogger('maskgen').warning('Invalid filter {} in group {}'.format( filter, self.name))
                return False
        return True

    def getOperation(self):
        op = {'name':self.name}
        op['arguments'] = {}
        bestsuffix = None
        ops = []
        for filter in self.filters:
            suffix = plugins.getPreferredSuffix(filter)
            if suffix is not None:
                bestsuffix = suffix
            currentop = plugins.getOperation(filter)
            ops.append(buildFilterOperation(currentop))
            for k,v in currentop.iteritems():
                if k == 'arguments' and v is not None:
                    for arg,definition in v.iteritems():
                        if arg not in op['arguments']:
                            op['arguments'][arg] = definition
                elif k not in op:
                    op[k] = v
        op['transitions'] = get_transitions(ops)
        return {'function':'custom',
                'operation':op,
                'command':'custom',
                'suffix': bestsuffix,
                'mapping':None,
                'group':'Sequence'
                }

class OperationGroupFilter(GroupFilter):

    def __init__(self, name, filters):
        GroupFilter.__init__(self,name,filters)
        self.operation = None

    def isValid(self):
        for filter in self.filters:
            if getOperation(filter) is None:
                logging.getLogger('maskgen').warning('Invalid operation {} in group {}'.format(filter, self.name))
                return False
        return True

def rankGenerateMask(setting):
    rank = 'metaaudioframesall'
    return rank.find(setting)

def chooseHigherRank(setting1, setting2):
    if rankGenerateMask(setting1) > rankGenerateMask(setting2):
        return setting1
    return setting1

def mergeKeys(dest_dict, source_dict):
    for k,v in source_dict.iteritems():
        if k not in dest_dict:
            dest_dict[k] = [v]
        else:
            dest_dict[k].append(v)
    return mergeKeys

class GroupFilterLoader:
    groups = {}

    def getAvailableFilters(self, operations_used=list()):
        p = plugins.getOperations()
        names = p.keys()

        # grab transition prefixes for last operation
        transitionsPre = [t.split('.')[0] for t in
                          p[operations_used[-1]]['operation']['transitions']] if operations_used else None

        result = []
        for op_name in names:
            if op_name not in operations_used:
                if transitionsPre is not None:
                    # grab transition prefixes for current op
                    op_transitions = [t.split('.')[0] for t in p[op_name]['operation']['transitions']]

                    # don't append and continue with loop if transitions don't match
                    if set(transitionsPre).isdisjoint(op_transitions):
                        continue
                result.append(op_name)
        return result

    def getLoaderKey(self):
        return "filtergroups"

    def getGroups(self):
        return self.groups.values()

    def getGroup(self, name):
        return self.groups[name] if name in self.groups else None

    def getGroupNames(self):
        return self.groups.keys()

    def _getOperation(self,name, filter=True):
        pluginOp = plugins.getOperation(name) if filter else self.getOperation(name)
        return buildFilterOperation(pluginOp)

    def _buildGroupOperation(self,grp, name, filter=True, warning=True):
        if grp is not None:
            if grp.operation is not None:
                return grp.operation
            includeInMask = dict()
            includeInMask['default'] = False
            rules = set()
            opt_params = dict()
            mandatory_params = dict()
            dependencies = dict()
            analysisOperations = set()
            generateMask = "meta"
            grp_categories = set()
            customFunctions = {}
            ops = []
            if filter and not grp.isValid():
                return None
            logging.getLogger('maskgen').info('Building group {} filter {}'.format(grp, name))
            compareparameters = {}
            for op in grp.filters:
                operation = self._getOperation(op)
                ops.append(operation)
                grp_categories.add(operation.category)
                for k,v in operation.includeInMask.iteritems():
                    if k in includeInMask:
                        includeInMask[k] = includeInMask[k] | v
                    else:
                        includeInMask[k] = v
                generateMask = chooseHigherRank(generateMask, operation.generateMask)
                addToSet(rules, operation.rules)
                addToMap(mandatory_params, operation.mandatoryparameters)
                addToMap(opt_params, operation.optionalparameters)
                addToSet(analysisOperations, operation.analysisOperations)
                addToMap(dependencies, operation.parameter_dependencies)
                compareparameters.update(operation.compareparameters)
                if operation.maskTransformFunction is not None:
                    mergeKeys(customFunctions, operation.maskTransformFunction)
            opt_params = dict([(k, v) for (k, v) in opt_params.iteritems() if k is not mandatory_params])
            transitions = get_transitions(ops)

            if len(customFunctions) > 0:
                for k in customFunctions:
                    if len(customFunctions[k]) > 0:
                        #TODO...not using this now...list vs. str issue
                        customFunctions[k] = customFunctions[k]
                    else:
                        customFunctions[k] = customFunctions[k][0]

            return Operation(name=name, category='Groups',
                             includeInMask=includeInMask,
                             generateMask=generateMask,
                             mandatoryparameters=mandatory_params,
                             description='User Defined',
                             optionalparameters=opt_params,
                             rules=list(rules),
                             transitions=transitions,
                             groupedOperations=grp.filters,
                             compareparameters=compareparameters,
                             groupedCategories=grp_categories,
                             analysisOperations=analysisOperations,
                             maskTransformFunction=customFunctions,
                             parameter_dependencies=dependencies)
            return grp.operation
        return getOperation(name, fake=True, warning=warning)

    def getOperation(self, name):
        grp = self.getGroup(name)
        try:
            return self._buildGroupOperation(grp, name, warning=False) if grp is not None else getOperation(name)
        except Exception as e:
            logging.getLogger('maskgen').error('Group Filter {} is in an inconsistent state: {} '.format(name, str(e)))
            return None

    def __init__(self):
        self.load()

    def getOperations(self,startType,endType):
        import copy
        p = copy.copy(plugins.getOperations(startType))
        for grp,v in self.groups.iteritems():
            if not v.isValid():
                continue
            try:
                grpOp = v.getOperation()
                transitions = [t.split('.')[0] for t in grpOp['operation']['transitions']]
                if startType is None or startType in transitions:
                    p[grp] =grpOp
            except Exception as e:
                logging.getLogger('maskgen').error('Cannot load group filter {} : {}'.format(grp,str(e)))
        return p

    def load(self, filterFactory=lambda k,v: GroupFilter(k, v)):
        global maskgenloader
        self.groups = {}
        newset = maskgenloader.get_key(self.getLoaderKey())
        if newset is not None:
            for k, v in newset.iteritems():
                if len(v) > 0:
                    group = filterFactory(k, v)
                    if group.isValid():
                        self.groups[k] = group
        for k,v in getFilters(self.getLoaderKey()).iteritems():
            if len(v) > 0:
                group = filterFactory(k, v)
                if group.isValid():
                    self.groups[k] = group

    def add(self, groupfilter):
        self.groups[groupfilter.name] = groupfilter

    def remove(self, name):
        self.groups.pop(name)

    def getName(self):
        return "Filters"

    def save(self):
        global maskgenloader
        image = {}
        for k, v in self.groups.iteritems():
            image[k] = v.filters
        maskgenloader.save(self.getLoaderKey(), image)


    def injectGroup(self, name, ops):
        self.groups[name] = OperationGroupFilter(name, ops)

    def getOperationWithGroups(self, name, fake=False, warning=True):
        """
        Search groups for operation name, as the name may be a group operation
        :param name:
        :param fake:
        :param warning:
        :return:
        @rtype: Operation
        """
        op = getOperation(name, fake=False, warning=False)
        if op is None:
            op = self.getOperation(name)
        if op is None:
            if fake:
                return getOperation(name, fake=True, warning=warning)
        return op

    def getOperationsWithinGroup(self, name, fake=False, warning=True):
        """
        Return a list of operations. If a grouped operation, return the operations in the group.
        :param name:
        :param fake:
        :param warning:
        :return:
        @rtype: Operation
        """
        op = getOperation(name, fake=False, warning=False)
        if op is None:
            grp = self.getGroup(name)
            if grp is not None:
                results = []
                for filter in grp.filters:
                    newop = self.getOperationsWithinGroup(filter,fake=fake,warning=warning)
                    results.extend(newop)
                return results
        if op is None:
            if fake:
                return [getOperation(name, fake=True, warning=warning)]
            else:
                return []
        return [op]


    def getOperationsByCategoryWithGroups(self, sourcetype, targettype):
        """
        :param name:
        :param fake:
        :param warning:
        :return:
        @rtype: Operation
        """
        res = dict(getOperationsByCategory(sourcetype, targettype))
        items = self.getOperations(sourcetype, targettype)
        if items is not None:
            for k, v in items.iteritems():
                res[k] = v
        return res


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
        GroupFilterLoader.load(self,filterFactory=lambda k,v: OperationGroupFilter(k,v))

    def _getOperation(self, name):
        return  getOperation(name, fake=True)

    def getAvailableFilters(self, operations_used=list()):
        has_generate_mask = set()
        groups_used = set([getOperation(op_name, fake=True).category for op_name in operations_used])
        for op_name in operations_used:
            real_op = getOperation(op_name, fake=True)
            has_generate_mask.add(real_op.generateMask)
        ops = getOperations()
        if len(operations_used) > 1:
            return []
        return [op_name for op_name in ops if op_name not in operations_used and (not \
            ("all" in has_generate_mask and ops[op_name].generateMask == "all")) \
                and not \
              getOperation(op_name, fake=True).category in groups_used]

    def getCategoryForGroup(self, groupName):
        if groupName in self.getGroupNames():
            return "Groups"
        return None

    def getAllOperations(self):
        return getOperations()

    def getCategoryForOperation(self, name):
        op = getOperation(name,fake=False,warning=False)
        if op is not None:
            return op.category
        return self.getCategoryForGroup(name)

    def getOperations(self,fileType):
        import copy
        p = copy.copy(plugins.getOperations(fileType))
        for grp,v in self.groups.iteritems():
            p[grp] = v.getOperation()
        return p

    def getOperation(self, name):
        grp = self.getGroup(name)
        return self._buildGroupOperation(grp, name, filter=False) if grp is not None else getOperation(name)

    def getOperations(self, startType, endType):
        cat = dict()
        cat['Groups'] = list()
        newset = maskgenloader.get_key(self.getLoaderKey())
        if newset is None:
            return cat
        deleteKeys  = []
        for group, content in newset.iteritems():
            if len(content) > 0:
                first_op = getOperation(content[0])
                if first_op is None:
                    deleteKeys.append(group)
                    continue
                for first_op_trans in first_op.transitions:
                    start = first_op_trans.split('.')[0]
                    if start != startType:
                        continue
                    second_op = getOperation(content[-1])
                    if second_op is None:
                        deleteKeys.append( group)
                        continue
                    for second_op_trans in second_op.transitions:
                        end = second_op_trans.split('.')[1]
                        if end == endType:
                            cat['Groups'].append(group)
                            continue
        for group in deleteKeys:
            newset.pop(group)
        return cat





