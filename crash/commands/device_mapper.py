# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import gdb
import argparse

from crash.commands import CrashCommand, CommandRuntimeError
from crash.types.blockdev import for_each_block_device
from crash.types.list import list_for_each_entry

mapped_device_type = gdb.lookup_type("struct mapped_device")

x = gdb.lookup_symbol("dm_table_supports_discards", None)[0]
b = gdb.block_for_pc(long(x.value().address))
dm_table_type = gdb.lookup_type("struct dm_table", b)

target_array = gdb.lookup_type("struct dm_target")
linear_c_type = gdb.lookup_type("struct linear_c")
multipath_type = gdb.lookup_type("struct multipath")
hash_cell_type = gdb.lookup_type("struct hash_cell")

# This doesn't work yet
#linear_target = gdb.lookup_symbol("linear_target", None)[0]
#multipath_target = gdb.lookup_symbol("multipath_target", None)[0]
#dm_blk_dops = gdb.lookup_symbol("dm_blk_dops", None)[0]
linear_target_addr = 0xffffffffa0613140
mpath_target_addr = 0xffffffffa07a4040
dm_blk_dops_addr = 0xffffffffa060d480

def gendisk_to_mapped_device(gendisk):
    return gendisk['private_data'].cast(mapped_device_type.pointer()).dereference()

def cast_to_real_dm_table(ptr):
    return ptr.cast(dm_table_type.pointer()).dereference()

def mapped_device_to_dm_table(md):
    return cast_to_real_dm_table(md['map'])

def dm_table_targets(table):
    t = table['targets'].type.target()
    upper_bound = table['num_targets'] - 1
    if upper_bound < 0:
        return None
    t = t.array(table['num_targets'] - 1)
    return table['targets'].dereference().cast(t)

def md_hash_cell(md):
    return md['interface_ptr'].cast(hash_cell_type.pointer()).dereference()

def md_dev_name(md):
    return md_hash_cell(md)['name'].string()

def dm_dev_name(dm_dev, verbose=False):
    if verbose:
        return dm_dev['bdev']['bd_disk']['disk_name'].string()
    else:
        return dm_dev['name'].string()

def target_name(target):
    table = cast_to_real_dm_table(target['table'])
    return table['md']['name'].string()

def target_private(target, typ):
    return target['private'].cast(typ.pointer()).dereference()

def linear_status(target, info=False, verbose=False):
    linear = target_private(target, linear_c_type)
    return "linear {} {}".format(dm_dev_name(linear['dev'], verbose),
                                 linear['start'])

def mpath_ps_rr_status(ps, path):
    pi_type = gdb.lookup_type("struct path_info")
    if path is None:
        return "0"

    p = path['pscontext'].cast(pi_type.pointer()).dereference()

    return "{}".format(p['repeat_count'])

def mpath_ps_status(ps, path):

    if ps['type']['name'].string() == "round-robin":
        return mpath_ps_rr_status(ps, path)
    else:
        raise Exception("Unknown {}".format(ps['type']['name'].string()))

def mpath_status(target, info=False, verbose=False):
    multipath = target_private(target, multipath_type)
    total_recs = 0
    out = ""

    if info:
        out += "{} {}".format(multipath['queue_size'],
                              multipath['pg_init_count'])
        total_recs = 2
    else:
        if multipath['queue_if_no_path']:
            out += "queue_if_no_path "
            total_recs += 1
        if multipath['pg_init_retries']:
            out += "pg_init_retries {} ".format(multipath['pg_init_retries'])
            total_recs += 2
        if multipath['pg_init_delay_msecs'] != 4294967295:
            out += "pg_init_delay_msecs {} ".format(multipath['pg_init_delay_msecs'])
            total_recs += 2
        if multipath['no_partitions']:
            out += "no_partitions "
            total_recs += 1
        if multipath['retain_attached_hw_handler']:
            out += "retain_attached_hw_handler "
            total_recs += 1

    if long(multipath['hw_handler_name']) != 0:
        out += "1 {}".format(multipath['hw_handler_name'].string())
    else:
        out += "0 "

    out += "{} ".format(multipath['nr_priority_groups'])

    pg_num = 0
    if multipath['next_pg']:
        pg_num = multipath['next_pg']['pg_num']
    elif multipath['current_pg']:
        pg_num = multipath['current_pg']['pg_num']
    elif multipath['nr_priority_groups']:
        pg_num = 1

    out += "{} ".format(pg_num)

    for pg in list_for_each_entry(multipath['priority_groups'],
                                  'struct priority_group', 'list'):
        if info:
            if pg['bypassed']:
                state = 'D'
            elif long(pg.address) == long(multipath['current_pg']):
                state = 'A'
            else:
                state = 'E'

            out += "{} ".format(state)
        else:
            out += "{} ".format(pg['ps']['type']['name'].string())

        out += "{} ".format(mpath_ps_status(pg['ps'], None))

        if info:
            args = 'info_args'
        else:
            args = 'table_args'
        out += "{} {} ".format(pg['nr_pgpaths'], pg['ps']['type'][args])
        for p in list_for_each_entry(pg['pgpaths'],
                                     'struct pgpath', 'list'):
            out += "{} ".format(dm_dev_name(p['path']['dev'], verbose))
            if info:
                active_state = 'F'
                if p['is_active']:
                    active_state = 'A'
                out += "{} {} ".format(active_state, p['fail_count'])
            out += "{} ".format(mpath_ps_status(pg['ps'], p['path']))

    return "multipath {} {}".format(total_recs, out)

class DeviceMapperCommand(CrashCommand):
    """oh hi"""
    def __init__(self):
        parser = argparse.ArgumentParser(prog="dm")
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-s', action='store_true', default=True)
        group.add_argument('-i', action='store_true', default=False)
        parser.add_argument('-v', action='store_true', default=False)
        parser.add_argument('-d', action='store_true', default=False)
        parser.add_argument("args", nargs=argparse.REMAINDER)

        super(DeviceMapperCommand, self).__init__('dm', parser)

    def execute(self, argv):
        info = argv.i
        verbose = argv.v
        for dev in for_each_block_device():
            if long(dev['fops']) == dm_blk_dops_addr:
                md = gendisk_to_mapped_device(dev)
                table = mapped_device_to_dm_table(md)

                targets = dm_table_targets(table)
                if not argv.d:
                    print("# {}".format(dev['disk_name'].string()))
                r = targets.type.range()
                for n in range(r[0], r[1] + 1):
                    target = targets[n]
                    if argv.d:
                        name = dev['disk_name'].string()
                    else:
                        name = md_dev_name(md)
                    print(" {}: {} {} ".format(name, target['begin'],
                                              target['len']), end='')
                    if target['type'] == linear_target_addr:
                        status = linear_status(target, info, verbose)
                    elif target['type'] == mpath_target_addr:
                        status = mpath_status(target, info, verbose)
                    else:
                        raise Exception("Unknown type")
                    print(status)

DeviceMapperCommand()
