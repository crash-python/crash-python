#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function

import gdb
import argparse
from crash.commands import CrashCommand, CommandRuntimeError
from crash.types.util import offsetof_type
import sys
import re

if sys.version_info.major >= 3:
    long = int

def to_number(num):
    try:
        return long(num)
    except ValueError as e:
        return long(num, 16)

class StructCommand(CrashCommand):
    """struct
Usage:
   struct <specifier> [-l <offset>] [-o|-r] [-p] [-f|-u] [-x|-d]
   [location] [-c <count> | <count>)

Options:
-l offset  structure.member or numeric offset
-o         show member offsets when displaying structure definitions. If used with
           an address or symbol argument, each member will be preceded by its
           virtual address.
"""
    def __init__(self):
        parser = argparse.ArgumentParser(prog="struct")
        parser.add_argument('-l', type=str, help="offset within struct either as a number of bytes or in \"structure.member\" format", metavar="offset/struct.member")
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-o', action='store_true', help="show member offsets when displaying structure definitions.If used with an address or symbol argument, each member will be preceded by its virtual address", default=False)
        group.add_argument('-r', action='store_true', default=False)
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-f', action='store_true', default=False)
        group.add_argument('-u', action='store_true', default=False)
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-x', action='store_true', default=False)
        group.add_argument('-d', action='store_true', default=False)
        parser.add_argument('-p', action='store_true', default=False)
        parser.add_argument('-F', action='store_true', default=False)
        parser.add_argument('spec', type=str, nargs=1)
        parser.add_argument('location', type=str, nargs='?')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-c', type=int, metavar="element-count")
        group.add_argument('count', type=int, nargs='?')

        self.ulongsize = gdb.lookup_type("unsigned long").sizeof

        super(StructCommand, self).__init__('struct', parser)

    def lookup_symbol(self, name):
        frame = None
        value = None
        block = None
        sym = None
        thread = gdb.selected_thread()
        if thread:
            frame = gdb.selected_frame()
        if frame:
            block = frame.block()

        if block:
            sym = gdb.lookup_symbol(name, block)[0]
        else:
            try:
                sym = gdb.lookup_symbol(name)[0]
            except gdb.error as e:
                pass
        if sym:
            if frame:
                value = sym.value(frame)
            else:
                value = sym.value()
        return value

    def format_struct(self, value, members):
        output = []
        if members:
            for member in members:
                v = value
                for component in member.split('.'):
                    v = v[component]
                output.append("  {} = {}".format(member, unicode(v)))
        else:
            output.append(unicode(value))
        return output

    def resolve_symbolic_offset(self, symoff):
        dot = symoff.find('.')
        if dot == -1:
            return None

        typename = symoff[:dot]
        member = symoff[dot+1:]

        if not typename.startswith("struct"):
            typename = "struct {}".format(typename)

        offtype = gdb.lookup_type(typename)
        if offtype:
            return offsetof_type(offtype, member)
            f = None
            for memb in components[1:]:
                if f and f.type.code & gdb.TYPE_CODE_PTR:
                    offtype = f.type.target()
                    offset = 0

                try:
                    f = offtype[memb]
                except KeyError as e:
                    raise CommandRuntimeError("Type `{}' has no member `{}'.".format(typename, memb))

                offtype = f.type
                offset += f.bitpos >> 3
        else:
            raise CommandRuntimeError("No such type `{}'".format(typename))

        return (offset, offtype)

    def format_output(self, argv):
        count = 1
        block = None
        frame = None
        value = None
        address = None

        # The parser ensures we only get one of these
        if argv.c:
            count = argv.c
        elif argv.count:
            count = argv.count

        thread = gdb.selected_thread()
        if thread:
            frame = gdb.selected_frame()
        if frame:
            block = frame.block()

        name = argv.spec[0]
        dot = name.find('.')
        members = None
        if dot > 0:
            name = argv.spec[0][:dot]
            members = argv.spec[0][dot + 1:].split(",")

        symval = self.lookup_symbol(name)
        if symval:
            objtype = symval.type
            address = symval.address
        else:
            if not name.startswith("struct "):
                name = "struct {}".format(name)
            objtype = gdb.lookup_type(name)

        offset = 0
        offtype = objtype
        if argv.l:
            try:
                try:
                    offset = long(argv.l)
                except ValueError as e:
                    offset = long(argv.l, 16)
            except ValueError as e:
                res = self.resolve_symbolic_offset(argv.l)
                if res is not None:
                    (offset, offtype) = res

        if argv.location:
            argv.location = argv.location.rstrip(",;.:")

            try:
                n = to_number(argv.location)
                if count or n > 2*1024*1024: #arbitrary
                    address = n
                else:
                    count = n
            except ValueError as e:
                mkpointer = False
                location = argv.location
                if location[0] == '&':
                    location = location[1:]

                components = location.split('.')
                location_symval = self.lookup_symbol(components[0])
                if not location_symval:
                    sym = gdb.lookup_global_symbol(components[0])
                    if sym:
                        location_symval = sym.value()

                if not location_symval:
                    raise CommandRuntimeError("Could not resolve location {}".format(argv.location))

                value = location_symval
                if value.type.code != gdb.TYPE_CODE_PTR:
                    value = value.address
                address = long(value)

                if len(components) > 1:
                    res = offsetof_type(location_symval.type,
                                        ".".join(components[1:]))

                    address += res[0]
                    if not argv.l:
                        objtype = res[1]
                    value = gdb.Value(address).cast(res[1].pointer())

                    if value.type.code != gdb.TYPE_CODE_PTR:
                        value = value.address
                    address = long(value)

                if not argv.F and str(offtype.pointer()) != str(value.type):
                    raise CommandRuntimeError("`{}' ({}) is not `{}'".format(
                                              argv.location, value.type,
                                              offtype.pointer()))
        if address:
            address -= offset
        elif offset:
            raise CommandRuntimeError("Offset provided without a location.")

        # Offset output
        if argv.o or address is None:
            return self.format_struct_layout(objtype, argv.o, address, members)

        # Raw output
        if argv.r:
            if address is None:
                raise CommandRuntimeError("Raw dump request without address being provided")
            line = gdb.lookup_type('unsigned long').array(1)
            charp = gdb.lookup_type('char').pointer()
            size = objtype.sizeof
            output = []
            for addr in range(address, address + size * count, size):
                value = gdb.Value(addr).cast(line.pointer()).dereference()
                output.append(value.cast(charp).string('ascii'))
                output.append("{:>16x}:  {:>016x} {:>016x}".format(addr,
                                            long(value[0]), long(value[1])))

            return output

        # Symbolic output
        output = []
        for n in range(0, count):
            value = gdb.Value(address).cast(objtype.pointer()).dereference()
            output += self.format_struct(value, members)
            address += objtype.sizeof
        return output

    def execute(self, argv):
        output = self.format_output(argv)
        if isinstance(output, list):
            print("\n".join(output))
        else:
            print(output)

    def step_into_subtype(self, field, members, depth):
        if not (field.type.code == gdb.TYPE_CODE_UNION or
                field.type.code == gdb.TYPE_CODE_STRUCT):
            return False

        if field.type.tag is None:
            return True

        if field.name is None:
            return True

        if members is None:
            return False

        for m in members:
            m = m.split('.')

            # Is there another component after this one?
            if len(m) > depth + 1 and m[depth] == field.name:
                return True
        return False

    def format_subtype(self, objtype, offset_width, address, base, members,
                       level=0, depth=0):
        output = []
        if level == 0 and not offset_width:
            level += 1
        indent_len = 4 * level
        indent = "{0:<{1}}".format('', indent_len)

        for field in objtype.fields():
            field_offset = field.bitpos // 8

            found = False
            if members and field.name is not None:
                for m in members:
                    m = m.split('.')
                    if len(m) > depth and m[depth] == field.name:
                        found = True
                if not found:
                    continue

            if self.step_into_subtype(field, members, depth):
                if field.type.code == gdb.TYPE_CODE_UNION:
                    prefix = "union"
                else:
                    prefix = "struct"

                width = indent_len
                if offset_width:
                    width += offset_width + 1
                addr = 0
                if address:
                    addr = address
                addr += field_offset

                name = ""
                if field.name:
                    name = " " + field.name
                    depth += 1
                subout = self.format_subtype(field.type, offset_width, addr,
                                             base, members, level + 1, depth)
                if subout:
                    tag = ""
                    if field.type.tag:
                        tag = " " + field.type.tag
                    output.append("{0:>{1}}{2}{3} {{".format('', width,
                                                           prefix, tag))
                    output += subout
                    output.append("{0:>{1}}}}{2};".format('', width, name))
                continue

            line = ""
            if offset_width:
                if address:
                    field_offset += address
                if base == 16:
                    tmp = "[{0:0{1}x}]".format(field_offset, self.ulongsize*2)
                else:
                    tmp = "[{0}]".format(field_offset)
                line += "{0:>{1}} ".format(tmp, offset_width)

            if field.bitsize > 0:
                line += "{3:<{4}}{0} {1} : {2};".format(field.type,
                                                  field.name, field.bitsize,
                                                  '', indent_len)
            elif self.is_func_ptr(field):
                line += "{1:<{2}}{0};".format(
                                self.format_func_ptr(field.name, field.type),
                                '', indent_len)
            else:
                line += "{2:<{3}}{0} {1};".format(field.type, field.name,
                                                  '', indent_len)
            output.append(line)
        return output

    def format_struct_layout(self, objtype, print_offset, address, members):
        output = []
        size = 0;
        if print_offset and address:
            size = len("[{0:{1}x}]".format(address, self.ulongsize*2)) + 2
        elif print_offset:
            size = len("[{}]".format(objtype.sizeof)) + 2
        base = 16
        if address is None:
            address = 0
            base = 10
        output.append("{0} {{".format(objtype))
        output += self.format_subtype(objtype, size, address, base, members)
        output.append("}")
        output.append("SIZE: {0}".format(objtype.sizeof))
        return output

    def is_func_ptr(self, field):
        return (field.type.code == gdb.TYPE_CODE_PTR and
                field.type.target().code == gdb.TYPE_CODE_FUNC)

    def format_func_ptr(self, name, typ):
        return "{} (*{})({})".format(typ.target().target(), name,
               ", ".join([str(f.type) for f in typ.target().fields()]))

StructCommand()
