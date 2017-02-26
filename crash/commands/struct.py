#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import argparse
from crash.commands import CrashCommand

def to_number(num):
    try:
        return long(num)
    except ValueError as e:
        return long(num, 16)

class StructCommand(CrashCommand):
    """struct
Usage:
   struct <specifier> [-l <offset>] [-o] [-r] [-p] [-f|-u] [-x|-d]
   [location] [-c <count> | <count>)

Options:
-l offset  structure.member or numeric offset
"""
    def __init__(self):
        parser = argparse.ArgumentParser(prog="struct")
        parser.add_argument('-l', type=str, help="offset within struct either as a number of bytes or in \"structure.member\" format", metavar="offset/struct.member")
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-o', action='store_true', default=False)
        group.add_argument('-r', action='store_true', default=False)
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-f', action='store_true', default=False)
        group.add_argument('-u', action='store_true', default=False)
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-x', action='store_true', default=False)
        group.add_argument('-d', action='store_true', default=False)
        parser.add_argument('-p', action='store_true', default=False)
        parser.add_argument('spec', type=str, nargs=1)
        parser.add_argument('location', type=str, nargs='?')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-c', type=int, metavar="element-count")
        group.add_argument('count', type=int, nargs='?')

        super(StructCommand, self).__init__('struct', parser)

    def lookup_symbol(self, name):
        frame = None
        value = None
        block = None
        thread = gdb.selected_thread()
        if thread:
            frame = gdb.selected_frame()
        if frame:
            block = frame.block()

        sym = gdb.lookup_symbol(name, block)[0]
        if sym:
            if frame:
                value = sym.value(frame)
            else:
                value = sym.value()
        return value

    def print_struct(self, value, members):
        if members:
            for member in members:
                v = value
                for component in member.split('.'):
                    v = v[component]
                print("  {} = {}".format(member, v))
        else:
            # gdb's output isn't utf-8 safe.
            print(value)

    def print_struct_layout(self, gdbtype, address):
        print(gdbtype)
        gdb.execute("ptype {}".format(str(gdbtype)))
        print(gdbtype)

    def execute(self, argv):
        count = None
        block = None
        frame = None
        value = None
        address = None

        if argv.c:
            count = argv.c

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

        if argv.location:
            argv.location = argv.location.rstrip(",;.:")

        symval = self.lookup_symbol(name)
        if symval:
            objtype = symval.type
            address = symval.address
        else:
            if not name.startswith("struct "):
                name = "struct {}".format(name)
            objtype = gdb.lookup_type(name)
            print(objtype)

        if argv.count:
            if argv.c:
                print("Count already specified using -c {}.".format(argv.c))
                return
            count = argv.count

        if count is None:
            count = 1

        offset = 0
        offtype = objtype
        if argv.l:
            try:
                try:
                    offset = long(argv.l)
                except ValueError as e:
                    offset = long(argv.l, 16)
            except ValueError as e:
                dot = argv.l.find('.')
                member = None
                if dot == -1:
                    print("Specifying a structure with no member means offset=0")
                    offset = 0
                else:
                    components = argv.l.split('.')
                    typename = components[0]
                    member = argv.l[dot + 1:]

                    if not typename.startswith("struct"):
                        typename = "struct {}".format(typename)

                    offtype = gdb.lookup_type(typename)
                    if offtype:
                        f = None
                        for memb in components[1:]:
                            if f and f.type.code & gdb.TYPE_CODE_PTR:
                                offtype = f.type.target()
                                offset = 0

                            try:
                                f = offtype[memb]
                            except KeyError as e:
                                print("Type `{}' has no member `{}'.".format(typename, memb))
                                return

                            offtype = f.type
                            offset += f.bitpos >> 3
                    else:
                        print("No such type `{}'".format(typename))
                        return

        if argv.location:
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
                    mkpointer = True
                    location = location[1:]

                components = location.split('.')
                location_symval = self.lookup_symbol(components[0])
                if location_symval:
                    v = location_symval
                    for memb in components[1:]:
                        v = v[memb]

                    if mkpointer:
                        v = v.address

                    if v.type.code != gdb.TYPE_CODE_PTR:
                        address = long(v.address)
                    else:
                        address = long(v)

                    if str(offtype.pointer()) != str(v.type):
                        print("`{}' ({}) is not `{} *'".format(argv.location, v.type, offtype))
                        return
        if address:
            address -= offset
        elif offset:
            print("Offset provided without a location.")
            return

        # Offset output
        if argv.o:
            for field in objtype:
                print(field)
            return


        # Raw output
        if argv.r:
            line = gdb.lookup_type('unsigned long').array(1)
            charp = gdb.lookup_type('char').pointer()
            size = objtype.sizeof
            for addr in range(address, address + size * count, size):
                value = gdb.Value(addr).cast(line.pointer()).dereference()
                print(value.cast(charp).string('ascii'))
                print("{:>16x}:  {:>016x} {:>016x}".format(addr, long(value[0]), long(value[1])))

            return

        if address is None or argv.o:
            self.print_struct_layout(objtype, address)
            return

        # Symbolic output
        for n in range(0, count):
            value = gdb.Value(address).cast(objtype.pointer()).dereference()
            self.print_struct(value, members)
            address += objtype.sizeof

StructCommand()
