from maskgen import tool_set
import unittest
import os


from maskgen.batch.permutations import *


class TestToolSet(unittest.TestCase):
    def test_chained(self):
        manager = PermuteGroupManager()
        num_4_iterator = lambda: xrange(1, 4 + 1,1).__iter__()
        manager.loadParameter('group_a', '1.num_4_iterator', num_4_iterator)
        manager.loadParameter('group_a','1.list',['1','2','3'].__iter__)
        self.assertTrue(manager.hasNext())
        self.assertEquals('1',manager.current('group_a','1.list'))
        self.assertEquals(1, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('2', manager.current('group_a', '1.list'))
        self.assertEquals(1, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('3', manager.current('group_a', '1.list'))
        self.assertEquals(1, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('1', manager.current('group_a', '1.list'))
        self.assertEquals(2, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('2', manager.current('group_a', '1.list'))
        self.assertEquals(2, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('3', manager.current('group_a', '1.list'))
        self.assertEquals(2, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('1', manager.current('group_a', '1.list'))
        self.assertEquals(3, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('2', manager.current('group_a', '1.list'))
        self.assertEquals(3, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('3', manager.current('group_a', '1.list'))
        self.assertEquals(3, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('1', manager.current('group_a', '1.list'))
        self.assertEquals(4, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('2', manager.current('group_a', '1.list'))
        self.assertEquals(4, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertTrue(manager.hasNext())
        self.assertEquals('3', manager.current('group_a', '1.list'))
        self.assertEquals(4, manager.current('group_a', '1.num_4_iterator'))
        manager.next()
        self.assertFalse(manager.hasNext())


def test_unchained(self):
    manager = PermuteGroupManager()
    num_4_iterator = lambda: xrange(1, 4 + 1, 1).__iter__()
    manager.loadParameter('group_a', '1.list', ['1', '2', '3'].__iter__)
    manager.loadParameter('group_a', '1.num_4_iterator', num_4_iterator)
    self.assertTrue(manager.hasNext())
    self.assertEquals('1', manager.current('group_a', '1.list'))
    self.assertEquals(1, manager.current('group_a', '1.num_4_iterator'))
    manager.next()
    self.assertTrue(manager.hasNext())
    self.assertEquals('2', manager.current('group_a', '1.list'))
    self.assertEquals(2, manager.current('group_a', '1.num_4_iterator'))
    manager.next()
    self.assertTrue(manager.hasNext())
    self.assertEquals('3', manager.current('group_a', '1.list'))
    self.assertEquals(3, manager.current('group_a', '1.num_4_iterator'))
    manager.next()
    self.assertFalse(manager.hasNext())

if __name__ == '__main__':
    unittest.main()