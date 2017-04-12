#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
from crash.arch import CrashArchitecture, register

class x86_64Architecture(CrashArchitecture):
    ident = "i386:x86-64"
    aliases = ["x86_64"]

    def __init__(self):
        super(x86_64Architecture, self).__init__()
        # PC for blocked threads
        self.rip = gdb.lookup_minimal_symbol("thread_return").value()
        self.ulong_type = gdb.lookup_type('unsigned long')

    def setup_thread(self, task):
        ulong_type = self.ulong_type

        rsp = task['thread']['sp'].cast(ulong_type.pointer())
        rbp = rsp.dereference().cast(ulong_type.pointer())
        rbx = (rbp - 1).dereference()
        r12 = (rbp - 2).dereference()
        r13 = (rbp - 3).dereference()
        r14 = (rbp - 4).dereference()
        r15 = (rbp - 5).dereference()

        # The two pushes that don't have CFI info
        # rsp += 2

        # ex = in_exception_stack(rsp)
        # if ex:
        #     print "EXCEPTION STACK: pid %d" % task['pid']

        thread.registers['rsp'].value = rsp
        thread.registers['rbp'].value = rbp
        thread.registers['rip'].value = self.rip
        thread.registers['rbx'].value = rbx
        thread.registers['r12'].value = r12
        thread.registers['r13'].value = r13
        thread.registers['r14'].value = r14
        thread.registers['r15'].value = r15
        thread.registers['cs'].value = 2*8
        thread.registers['ss'].value = 3*8

register(x86_64Architecture)
