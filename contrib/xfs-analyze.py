#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
# bsc#1025860

# This script cross references items in the AIL with buffers and inodes
# locked in every task's stack

from crash.types.list import list_for_each_entry
from crash.util import container_of
import gdb

dentry_type = gdb.lookup_type('struct dentry')
ail_type = gdb.lookup_type('struct xfs_ail')
xfs_log_item_type = gdb.lookup_type('struct xfs_log_item')
xfs_inode_log_item_type = gdb.lookup_type('struct xfs_inode_log_item')
ail = gdb.Value(0xffff885e3b9e3a40).cast(ail_type.pointer()).dereference()
print ail

# This should go into a crash.types.rwsem
RWSEM_ACTIVE_MASK = 0xffffffffL
RWSEM_UNLOCKED_VALUE = 0
RWSEM_ACTIVE_BIAS = 1
RWSEM_WAITING_BIAS = 0xffffffff00000000L
RWSEM_ACTIVE_READ_BIAS = 1
RWSEM_ACTIVE_WRITE_BIAS = 0xffffffff00000001L

def inode_paths(inode):
    for dentry in list_for_each_entry(inode['i_dentry'], dentry_type, ''):
        names = [dentry['d_name']['name'].string()]
        parent = dentry['d_parent']
        while parent.address != parent['d_parent'].address:
            names.insert(0, parent['d_name']['name'].string())
            parent = parent['d_parent']

        yield '/'.join(names)

def rwsem_read_trylock(rwsem):
    count = long(rwsem['count']) & 0xffffffffffffffffL
    if count == 0:
        return True
    if count & RWSEM_ACTIVE_WRITE_BIAS:
        return False
    if count >= 0:
        return True

locked_inodes = {}

def check_item(item):
    if item['li_type'] == 0x123b: # inode
        iitem = container_of(item, xfs_inode_log_item_type, 'ili_item')
        if iitem['ili_inode']['i_pincount']['counter'] > 0:
#            print "<pinned {:16x}>".format(iitem['ili_inode'].address)
            return 1
        if not rwsem_read_trylock(iitem['ili_inode']['i_lock']['mr_lock']):
            inode = iitem['ili_inode']['i_vnode'].address
#            print "<locked {}>".format(inode)
            print oct(int(inode['i_mode']))
            if long(inode) in locked_inodes:
                print "in AIL multiple times"
            else:
                locked_inodes[long(inode)] = iitem['ili_inode']
#            for path in inode_paths(inode):
#                print path
            return 2
#        print "<ok>"
    elif item['li_type'] == 0x123c: # buffer
        pass
    else:
        print "*** Odd type {}".format(item['li_type'])
    return 0

# superblock ffff885e2ec11000
# fs_info 0xffff885e33f7e000
# m_ail 0xffff885e3b9e3a40

last_pushed = ail['xa_last_pushed_lsn']
target = ail['xa_target']

found = None
count = 0
last_lsn = 0
total = 0
for item in list_for_each_entry(ail['xa_ail'], xfs_log_item_type, 'li_ail'):

    # xfsaild_push fast forwards to the last pushed before starting
    # pushes are two (three, kind of) stages for inodes, which most of
    # the ail list is for this report
    # 1) attempt to push the inode item, which writes it back to its buffer
    # 2) upon success, attempt to push the buffer
    # 3) when the buffer is successfully written, the callback is called
    #    which removes the item from the list
    # The list prior to last_pushed contains the items for which we're
    # waiting on writeback.
    if item['li_lsn'] < last_pushed:
        count += 1
        continue
    if last_lsn == 0:
        print "Skipped {} items before last_pushed ({})".format(count, last_pushed)
        count = 0
    elif item['li_lsn'] > target:
        print "** Target LSN reached: {}".format(target)
        break

    total += 1

    if last_lsn != item['li_lsn']:
        if last_lsn != 0:
            print "*** {:<4} total items for LSN {} ({} ready, {} pinned, {} locked)".format(count, last_lsn, ready, pinned, locked)
            count = 0
#        print "*** Processing LSN {}".format(item['li_lsn'])
        pinned = 0
        locked = 0
        ready = 0

    ret = check_item(item)
    if ret == 1:
        pinned += 1
    elif ret == 2:
        locked += 1
    else:
        if locked and ready == 0:
            print "<{} locked>".format(locked)
        ready += 1

    last_lsn = item['li_lsn']
    count += 1

    # We only care about the first 100 items
    if count > 104:
        break

checked = 0
dead = 0
for thread in gdb.selected_inferior().threads():
    thread.switch()
    try:
        f = gdb.selected_frame()
        while True:
            f = f.older()
            fn = f.function()
            if not fn:
                break
            if fn.name == '__fput':
                fp = f.read_var('file')
                inode = fp['f_path']['dentry']['d_inode']
                checked += 1
                if inode in locked_inodes:
                    print inode
                break
            if fn.name == 'vfs_create':
                try:
                    inode = f.read_var('dir')
                except ValueError as e:
                    print f
                    inode = None
                checked += 1
                if long(inode) in locked_inodes:
                    print "PID {} inode {}".format(thread.ptid, hex(long(inode)))
                    dead += 1
                break

    except gdb.error as e:
        pass

print "Checked {} inodes in __fput or vfs_create".format(checked)
print "Total items processed: {}".format(total)
print "Total inodes tracked: {}".format(len(locked_inodes.keys()))
print "Total inodes locked and waiting: {}".format(dead)
