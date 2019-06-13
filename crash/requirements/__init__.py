# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from crash.exceptions import IncompatibleGDBError

# Perform some sanity checks to ensure that we can actually work
import gdb

try:
    x1 = gdb.Target
    del x1
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Target")

try:
    x2 = gdb.lookup_symbol('x', None)
    del x2
except TypeError as e:
    raise IncompatibleGDBError("a compatible gdb.lookup_symbol")

try:
    x3 = gdb.MinSymbol
    del x3
except AttributeError as e:
    raise IncompatibleGDBError("gdb.MinSymbol")

try:
    x4 = gdb.Register
    del x4
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Register")

try:
    x5 = gdb.Symbol.section
    del x5
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Symbol.section")

try:
    x6 = gdb.Inferior.new_thread
    del x6
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Inferior.new_thread")

try:
    x7 = gdb.Objfile.architecture
    del x7
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Objfile.architecture")
