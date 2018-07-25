# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Perform some sanity checks to ensure that we can actually work
import gdb

try:
    x = gdb.Target
except AttributeError, e:
    raise RuntimeError("the installed gdb doesn't provide gdb.Target")

try:
    x = gdb.lookup_symbol('x', None)
except TypeError, e:
    raise RuntimeError("the installed gdb doesn't support looking up symbols without a gdb.Block")

try:
    x = gdb.MinSymbol
except AttributeError, e:
    raise RuntimeError("the installed gdb doesn't provide gdb.MinSymbol")

try:
    x = gdb.Register
except AttributeError, e:
    raise RuntimeError("the installed gdb doesn't provide gdb.Register")

try:
    x = gdb.Symbol.section
except AttributeError, e:
    raise RuntimeError("the installed gdb doesn't provide gdb.Symbol.section")

try:
    x = gdb.Inferior.new_thread
except AttributeError, e:
    raise RuntimeError("the installed gdb doesn't provide gdb.Inferior.new_thread")

try:
    x = gdb.Objfile.architecture
except AttributeError, e:
    raise RuntimeError("the installed gdb doesn't provide gdb.Objfile.architecture")

del x
