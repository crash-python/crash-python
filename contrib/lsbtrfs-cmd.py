#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

path = "/lib/modules/4.4.20-6.gd2e08c5-default/kernel/fs/btrfs/btrfs.ko"

from crash.types.list import list_for_each_entry
import gdb
import uuid
from crash.commands import CrashCommand

class LSBtrfs(CrashCommand):
    """
    doc
    """
    def __init__(self):
        CrashCommand.__init__(self, "lsbtrfs", None)


    def execute(self, argv):
        super_blocks = gdb.lookup_symbol('super_blocks', None)[0].value()
        sbtype = gdb.lookup_type('struct super_block')

        try:
            btrfs_fs_info_type = gdb.lookup_type('struct btrfs_fs_info')
        except gdb.error:
            # Load the module if it's not loaded yet
            module_type = gdb.lookup_type('struct module')

            modules = gdb.lookup_symbol('modules', None)[0].value()
            for module in list_for_each_entry(modules, module_type, 'list'):
                if module['name'].string() == "btrfs":
                    addr = module['module_core']
                    gdb.execute("add-symbol-file {} {}".format(path, addr))
            btrfs_fs_info_type = gdb.lookup_type('struct btrfs_fs_info')

        for sb in list_for_each_entry(super_blocks, sbtype, 's_list'):
            if sb['s_type']['name'].string() == "btrfs":
                fs_info = gdb.Value(sb['s_fs_info']).cast(btrfs_fs_info_type.pointer())

                u = 0
                for i in range(0, 16):
                    u <<= 8
                    u += int(fs_info['fsid'][i])
                u = uuid.UUID(int=u)
                print "{} -> {} {}".format(sb.address, sb['s_id'].string(), u)

LSBtrfs()
