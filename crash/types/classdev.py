# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Iterable

import gdb

from crash.types.klist import klist_for_each
from crash.util import struct_has_member, container_of
from crash.util.symbols import Types, TypeCallbacks

types = Types(['struct device', 'struct device_private'])

class ClassdevState(object):
    class_is_private = True

    #v5.1-rc1 moved knode_class from struct device to struct device_private
    @classmethod
    def _setup_iterator_type(cls, gdbtype):
        if struct_has_member(gdbtype, 'knode_class'):
            cls.class_is_private = False


type_cbs = TypeCallbacks([ ('struct device',
                            ClassdevState._setup_iterator_type) ])

def for_each_class_device(class_struct: gdb.Value,
                          subtype: gdb.Value=None) -> Iterable[gdb.Value]:
    klist = class_struct['p']['klist_devices']

    container_type = types.device_type
    if ClassdevState.class_is_private:
        container_type = types.device_private_type

    for knode in klist_for_each(klist):
        dev = container_of(knode, container_type, 'knode_class')
        if ClassdevState.class_is_private:
            dev = dev['device'].dereference()

        if subtype is None or int(subtype) == int(dev['type']):
            yield dev
