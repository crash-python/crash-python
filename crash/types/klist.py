# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.util import container_of
from crash.types.list import list_for_each_entry
from crash.exceptions import CorruptedError
from crash.infra import CrashBaseClass, export

class KlistCorruptedError(CorruptedError):
    pass

class TypesKlistClass(CrashBaseClass):
    __types__ = [ 'struct klist_node', 'struct klist' ]

    @export
    def klist_for_each(self, klist):
        if klist.type == self.klist_type.pointer():
            klist = klist.dereference()
        elif klist.type != self.klist_type:
            raise TypeError("klist must be gdb.Value representing 'struct klist' or 'struct klist *' not {}"
                            .format(klist.type))

        for node in list_for_each_entry(klist['k_list'],
                                        self.klist_node_type, 'n_node'):
            if node['n_klist'] != klist.address:
                raise KlistCorruptedError("Corrupted")
            yield node

    @export
    def klist_for_each_entry(self, klist, gdbtype, member):
        for node in klist_for_each(klist):
            if node.type != self.klist_node_type:
                raise TypeError("Type {} found. Expected {}.".format(node.type), self.klist_node_type.pointer())
            yield container_of(node, gdbtype, member)
