#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

path = "/lib/modules/3.0.101-0.47.90-default/kernel/fs/xfs/xfs.ko"

from crash.types.list import list_for_each_entry
import gdb
import uuid
from crash.commands import CrashCommand

class LSXfs(CrashCommand):
    """
    doc
    """
    def __init__(self):
        CrashCommand.__init__(self, "lsxfs", None)


    def execute(self, argv):
        super_blocks = gdb.lookup_symbol('super_blocks', None)[0].value()
        sbtype = gdb.lookup_type('struct super_block')

        try:
            xfs_mount_type = gdb.lookup_type('struct xfs_mount')
        except gdb.error:
            # Load the module if it's not loaded yet
            module_type = gdb.lookup_type('struct module')

            modules = gdb.lookup_symbol('modules', None)[0].value()
            for module in list_for_each_entry(modules, module_type, 'list'):
                if module['name'].string() == "xfs":
                    addr = module['module_core']
                    gdb.execute("add-symbol-file {} {}".format(path, addr))
            xfs_mount_type = gdb.lookup_type('struct xfs_mount')

        for sb in list_for_each_entry(super_blocks, sbtype, 's_list'):
            if sb['s_type']['name'].string() == "xfs":
                xfs_mount = gdb.Value(sb['s_fs_info']).cast(xfs_mount_type.pointer())

                print("{} -> {}".format(sb.address, sb['s_id'].string()))

LSXfs()
