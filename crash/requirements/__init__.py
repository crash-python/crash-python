# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from crash.exceptions import IncompatibleGDBError

# Perform some sanity checks to ensure that we can actually work
import gdb

try:
    x = gdb.Target
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Target")

try:
    x = gdb.lookup_symbol('x', None)
except TypeError as e:
    raise IncompatibleGDBError("a compatible gdb.lookup_symbol")

try:
    x = gdb.MinSymbol
except AttributeError as e:
    raise IncompatibleGDBError("gdb.MinSymbol")

try:
    x = gdb.Register
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Register")

try:
    x = gdb.Symbol.section
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Symbol.section")

try:
    x = gdb.Inferior.new_thread
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Inferior.new_thread")

try:
    x = gdb.Objfile.architecture
except AttributeError as e:
    raise IncompatibleGDBError("gdb.Objfile.architecture")

del x
