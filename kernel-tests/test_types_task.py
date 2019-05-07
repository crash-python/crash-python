# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

import crash.types.task as tasks

class TestTasks(unittest.TestCase):
    def setUp(self):
        self.task_struct_type = gdb.lookup_type('struct task_struct')

    def test_thread_group_leader_iteration(self):
        count = 0
        for leader in tasks.for_each_thread_group_leader():
            self.assertTrue(type(leader) is gdb.Value)
            self.assertTrue(leader.type == self.task_struct_type)
            self.assertTrue(int(leader['exit_signal']) >= 0)
            count += 1

        self.assertTrue(count > 0)

    def test_thread_group_iteration(self):
        count = 0
        for leader in tasks.for_each_thread_group_leader():
            for thread in tasks.for_each_thread_in_group(leader):
                self.assertTrue(type(thread) is gdb.Value)
                self.assertTrue(thread.type == self.task_struct_type)
                self.assertTrue(int(thread['exit_signal']) < 0)
                count += 1

        self.assertTrue(count > 0)

    def test_iterate_all_tasks(self):
        count = 0
        for task in tasks.for_each_all_tasks():
            self.assertTrue(type(task) is gdb.Value)
            self.assertTrue(task.type == self.task_struct_type)
            count += 1

        self.assertTrue(count > 0)
