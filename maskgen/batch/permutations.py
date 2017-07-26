from threading import Lock, local
import logging

"""
   This package manages permutaitons of parameters for the batch process.  Basically, each permutation is an iterator.
   Even random generators can be considered iterators that never exhaust their supply (never raise EndOfResource exception).
   Permutations are organized into groups.  There are two kinds of groups: global and chained.
   Global groups are denoted with name __global__.  When advanced by the PermuteGroupManager, all the iterators are advanced.
   Any one iterator in the global group that runs out of resources raises an EndOfResource exception.
   Chained groups are made of chained iterators, defined in the order they are constructed within the group.
   Each chained group as its own unique name. The first element of a chained is the last iterator to be incremented (next()).
   Consider a chain group 'mygroup' with three iterators int[1:2], ['a','b'] and ['x','y'], added in the listed order.
   The resulting values will be : x a 1, y a 1, x b 1, y b 1, x a 1, y a 2, x b 2, y b 2.

"""
class EndOfResource(Exception):

    def __init__(self, resource):
        self.resource = resource
    def __str__(self):
        return "Resource {} depleted".format(self.resource)

def randomGenerator(function):
    while True:
        yield function()

def randomGeneratorFactory(function):
    return lambda : randomGenerator(function)

class PermuteGroupElement:

    """
   A single iterator and a function to reset the iterator.
   An iterator has a dependent.  If chained, the iterator will send next() the dependent
   prior to itself.  Only when the dependent is depleted will this element fetch the next
   item of its iterator just after reseting the dependent.
    """
    def __init__(self,name, toIteratorFunction, dependent=None):
        self.name = name
        self.factory = toIteratorFunction
        self.iterator = toIteratorFunction()
        self.dependent = dependent
        self.current = local()
        #self.current = self.iterator.next()

    def next(self,chained=False):
        """
        :param chained: if True, increase dependents first
        :return:
        """

        if self.dependent is not None and chained:
            try:
                self.dependent.next(chained=chained)
            except Exception as e:
                # first reset since fetching next may cause this element to throw an end of resource exception
                self.dependent.reset()
                # throws an exception to caller
                self.current.item = self.iterator.next()
            try:
                self.current.item
            except:
                self.current.item = self.iterator.next()
        else:
            self.current.item = self.iterator.next()
        return self.current.item

    def reset(self):
        self.iterator = self.factory()
        self.current.item = self.iterator.next()

    def getCurrent(self):
        try:
            return self.current.item
        except:
            self.current.item = self.iterator.next()
            return self.current.item


class PermuteGroup:
    """
    A single group of iterators
    """
    last_created = None
    first_created = None
    """
    @type iterators : dict[String, PermuteGroupElement]
    """

    def __init__(self, group_name, chained=False, dir ='.'):
        self.name = group_name
        self.iterators = dict()
        self.completed = set()
        self.chained = chained
        self.dir = dir

    def addIteratorFactory(self, spec_name, factory_function):
        """
        :param spec_name:
        :param factory_function: creates an iterator
        :return:
        @type spec_name: str
        """
        if spec_name not in self.iterators:
            element = PermuteGroupElement(spec_name, factory_function)
            if self.last_created is not None:
               self.last_created.dependent = element
            if self.first_created is  None:
               self.first_created = element
            self.iterators[spec_name] = element
            self.last_created = element

    def next(self):
        """
        Advanced all iterators if not chanined, or advance the next iterator on the
        iterator dependency list.
        """
        if not self.chained:
            for name, it in self.iterators.iteritems():
                try:
                    it.next()
                except:
                    self.completed.add(name)
                    # keep going to all resources have been used
                    try:
                        logging.getLogger('maskgen').info('reseting ' + name)
                        it.reset()
                    except Exception as eor:
                        logging.getLogger('maskgen').info(str(eor))
                        # at this point, a resource cannot be reset (exhausted) or something else bad happened
                        self.completed = set(self.iterators.keys())
                        raise eor
        else:
            try:
                self.first_created.next(chained=True)
            except Exception as e:
                self.first_created.reset()
                # at this point, all are exhausted
                self.completed = set(self.iterators.keys())


    def has_specification(self, name):
        return name  in self.iterators

    def current(self, name):
        if name not in self.iterators:
            raise ValueError('Undefined specifiction {} in permute group {}'.format(name, self.name))
        element = self.iterators[name]
        return element.getCurrent()

    def hasNext(self):
        return len(self.completed) != len(self.iterators)

    def reset(self):
        for it in self.iterators.values():
            it.reset()
        self.completed.clear()

    def save(self):
        pass

class PermuteGroupManager:

    """
    @type groups: Dict[string, PermuteGroup]
    """

    def __init__(self,dir='.'):
        self.groups = dict()
        self.lock = Lock()

    def loadParameter(self, group_name, spec_name, iterator_factory):
        name = group_name if group_name is not None else '__global__'
        with self.lock:
            if name not in self.groups:
                self.groups[name] = PermuteGroup(name,chained=name!='__global__',dir=dir)
            if not self.groups[name].has_specification(spec_name):
                self.groups[name].addIteratorFactory(spec_name, iterator_factory)


    def next(self):
        """
        Advance all groups. For chained groups, only one iterator ill be advanced as deteremined by
        the PermuteGrouop
        :return:
        """
        with self.lock:
            for group_name,grp in self.groups.iteritems():
                if not grp.hasNext():
                    raise EndOfResource('Resources depleted for group {}'.format(group_name))
            for group_name, group in self.groups.iteritems():
                group.next()

    def has_specification(self, group_name, spec_name):
        """
        :param group_name: if None, assume '__global__'
        :param spec_name:
        :return: True if the iterator is defined for the provided group
        """
        name = group_name if group_name is not None else '__global__'
        return name in self.groups and self.groups[name].has_specification(spec_name)

    def current(self, group_name, spec_name):
        """
        Obtain the current item of the given iterator in the given group
        :param group_name: if None, assume '__global__'
        :param spec_name:
        :return: current element of the requested iterator
        """
        name  = group_name if group_name is not None else '__global__'
        if name not in self.groups:
            raise ValueError('Undefined permutation group ' + name)
        group = self.groups[name]
        with self.lock:
            return group.current(spec_name)

    def hasNext(self):
        for grp in self.groups.values():
            if grp.hasNext():
                return True
        return False

    def save(self):
        for group in self.groups.values():
            group.save()
