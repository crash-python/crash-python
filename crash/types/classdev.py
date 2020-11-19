# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
The crash.types.classdev module offers helpers to work with class devices.
"""

from typing import Iterable

import gdb

from crash.types.klist import klist_for_each
from crash.util import struct_has_member, container_of
from crash.util.symbols import Types, TypeCallbacks

types = Types(['struct device', 'struct device_private'])

class ClassdevState:
    _class_is_private = True

    @classmethod
    def setup_iterator_type(cls, gdbtype: gdb.Type) -> None:
        """
        Detect whether to iterate the class list using ``struct device``
        or ``struct device_private``.

        Linux v5.1-rc1 moved ``knode_class`` from ``struct device`` to
        ``struct device_private``.  We need to detect it here to ensure
        list iteration works properly.

        Meant to be used as a TypeCallback.

        Args:
            gdbtype: The ``struct device`` type.
        """
        if struct_has_member(gdbtype, 'knode_class'):
            cls._class_is_private = False

    @classmethod
    def class_is_private(cls) -> bool:
        """
        Returns whether the class device uses ``struct device_private``

        Meant to be used only be crash.types.classdev.
        """
        return cls._class_is_private


type_cbs = TypeCallbacks([('struct device',
                           ClassdevState.setup_iterator_type)])

def for_each_class_device(class_struct: gdb.Value,
                          subtype: gdb.Value = None) -> Iterable[gdb.Value]:
    """
    Iterate over the list of class devices

    Args:
        class_struct: The class of devices to iterate
        subtype: A ``struct device_type *`` to use to filter the results.
            The value must be of type ``struct device_type *`` and will
            be used to compare against the ``type`` field of each
            ``struct device``.

    Yields:
        :obj:`gdb.Value`: A device on the class's device list.  The value is
        of type ``struct device``.
    """
    klist = class_struct['p']['klist_devices']

    container_type = types.device_type
    if ClassdevState.class_is_private():
        container_type = types.device_private_type

    for knode in klist_for_each(klist):
        dev = container_of(knode, container_type, 'knode_class')
        if ClassdevState.class_is_private():
            dev = dev['device'].dereference()

        if subtype is None or int(subtype) == int(dev['type']):
            yield dev
