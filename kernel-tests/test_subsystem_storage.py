# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb
import io
import sys
import re

import crash.subsystem.storage as storage
import crash.subsystem.filesystem as fs
import crash.util as util
from crash.types.list import list_for_each_entry

class TestSubsystemFilesystem(unittest.TestCase):
    nullptr = 0x0
    poisonptr = 0xdead000000000100

    def setUp(self):
        self.char_p_type = gdb.lookup_type('char').pointer()
        self.super_block_type = gdb.lookup_type('struct super_block')
        self.inode_type = gdb.lookup_type('struct inode')
        self.device_type  = gdb.lookup_type('struct device')
        self.block_device_type  = gdb.lookup_type('struct block_device')
        self.gendisk_type  = gdb.lookup_type('struct gendisk')
        self.hd_struct_type  = gdb.lookup_type('struct hd_struct')

    def get_blockdev_superblock(self):
        return gdb.lookup_symbol('blockdev_superblock', None)[0].value()

    def get_block_device(self):
        all_bdevs = gdb.lookup_symbol('all_bdevs', None)[0].value()
        for bdev in list_for_each_entry(all_bdevs, self.block_device_type,
            'bd_list'):
            if int(bdev['bd_disk']) != 0 and int(bdev['bd_part']) != 0:
                return bdev
        return None

    def get_gendisk(self):
        all_bdevs = gdb.lookup_symbol('all_bdevs', None)[0].value()
        for bdev in list_for_each_entry(all_bdevs, self.block_device_type,
            'bd_list'):
            if int(bdev['bd_disk']) != 0:
                return bdev['bd_disk'].dereference()
        return None

    def get_hd_struct(self):
        all_bdevs = gdb.lookup_symbol('all_bdevs', None)[0].value()
        for bdev in list_for_each_entry(all_bdevs, self.block_device_type,
            'bd_list'):
            if int(bdev['bd_part']) != 0:
                return bdev['bd_part'].dereference()
        return None

    def get_filesystem_inode(self):
        for sb in fs.for_each_super_block():
            if fs.super_fstype(sb) != "bdev":
                return sb['s_root']['d_inode'].dereference()

        raise RuntimeError("No file system supers?")

    def get_block_device_inode(self):
        bdev_sb = self.get_blockdev_superblock()
        for inode in list_for_each_entry(bdev_sb['s_inodes'], self.inode_type,
                                         'i_sb_list'):
            return inode

    def get_blockdev_filesystem(self):
        for sb in fs.for_each_super_block():
            fstype = sb['s_type']['name'].string()
            print(f"{int(sb['s_bdev']):#x} name={fstype}")
            if int(sb['s_bdev']) != 0:
                return sb

        raise RuntimeError("No block device supers?")

    @unittest.skip
    def test_for_each_bio_in_stack(self):
        """This requires a dump that has a bio in flight to test"""
        pass

    def test_for_each_block_device_unfiltered(self):
        disk_type = storage.symvals.disk_type
        part_type = storage.symvals.part_type
        for bdev in storage.for_each_block_device():
            self.assertTrue(type(bdev) is gdb.Value)
            self.assertTrue(bdev.type == storage.types.gendisk_type or
                            bdev.type == storage.types.hd_struct_type)

    def test_for_each_block_device_filtered_for_disk(self):
        disk_type = storage.symvals.disk_type
        for bdev in storage.for_each_block_device(disk_type):
            self.assertTrue(type(bdev) is gdb.Value)
            self.assertTrue(bdev.type == storage.types.gendisk_type)

    def test_for_each_block_device_filtered_nullptr(self):
        null_type = util.get_typed_pointer(self.nullptr,
                                           storage.types.device_type_type)

        # The pointer is only used for comparison so we won't raise
        # an exception but we won't get any results either.
        for bdev in storage.for_each_block_device(null_type.dereference()):
            self.assertTrue(False)

    def test_for_each_block_device_filtered_poisonptr(self):
        null_type = util.get_typed_pointer(self.poisonptr,
                                           storage.types.device_type_type)

        # The pointer is only used for comparison so we won't raise
        # an exception but we won't get any results either.
        for bdev in storage.for_each_block_device(null_type.dereference()):
            self.assertTrue(False)

    def test_for_each_disk(self):
        for bdev in storage.for_each_disk():
            self.assertTrue(type(bdev) is gdb.Value)
            self.assertTrue(bdev.type == storage.types.gendisk_type)

    def test_for_each_block_device_filtered_for_partitions(self):
        part_type = storage.symvals.part_type
        for bdev in storage.for_each_block_device(part_type):
            self.assertTrue(type(bdev) is gdb.Value)
            self.assertTrue(bdev.type == storage.types.hd_struct_type)

    def test_block_device_name(self):
        bdev = self.get_block_device()
        self.assertTrue(type(bdev) is gdb.Value)
        self.assertTrue(bdev.type == self.block_device_type)
        name = storage.block_device_name(bdev)
        self.assertTrue(type(name) is str)

    def test_block_device_name_nullptr(self):
        bdev = util.get_typed_pointer(self.nullptr, self.block_device_type).dereference()
        self.assertTrue(type(bdev) is gdb.Value)
        self.assertTrue(bdev.type == self.block_device_type)
        with self.assertRaises(gdb.NotAvailableError):
            name = storage.block_device_name(bdev)

    def test_block_device_name_poisonptr(self):
        bdev = util.get_typed_pointer(self.poisonptr, self.block_device_type).dereference()
        self.assertTrue(type(bdev) is gdb.Value)
        self.assertTrue(bdev.type == self.block_device_type)
        with self.assertRaises(gdb.NotAvailableError):
            name = storage.block_device_name(bdev)

    def test_is_bdev_inode(self):
        inode = self.get_block_device_inode()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)
        self.assertTrue(storage.is_bdev_inode(inode))

    def test_is_bdev_inode_fs_inode(self):
        inode = self.get_filesystem_inode()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)
        self.assertFalse(storage.is_bdev_inode(inode))

    def test_is_bdev_inode_null_inode(self):
        inode = util.get_typed_pointer(self.nullptr, self.inode_type)
        inode = inode.dereference()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)
        with self.assertRaises(gdb.NotAvailableError):
            x = storage.is_bdev_inode(inode)

    def test_is_bdev_inode_poison_inode(self):
        inode = util.get_typed_pointer(self.poisonptr, self.inode_type)
        inode = inode.dereference()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)
        with self.assertRaises(gdb.NotAvailableError):
            x = storage.is_bdev_inode(inode)

    def test_inode_on_bdev_bdev_inode(self):
        bdev_sb = self.get_blockdev_superblock()
        inode = self.get_block_device_inode()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)
        bdev = storage.inode_on_bdev(inode)
        self.assertTrue(type(bdev) is gdb.Value)
        self.assertTrue(bdev.type == self.block_device_type)
        self.assertTrue(inode['i_sb'] == bdev_sb)
        self.assertTrue(fs.super_fstype(inode['i_sb']) == "bdev")

    def test_inode_on_bdev_fs_inode(self):
        bdev_sb = self.get_blockdev_superblock()
        inode = self.get_filesystem_inode()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)
        bdev = storage.inode_on_bdev(inode)
        self.assertTrue(type(bdev) is gdb.Value)
        self.assertTrue(bdev.type == self.block_device_type)
        self.assertFalse(inode['i_sb'] == bdev_sb)
        self.assertFalse(fs.super_fstype(inode['i_sb']) == "bdev")

    def test_inode_on_bdev_null_inode(self):
        inode = util.get_typed_pointer(self.nullptr, self.inode_type)
        inode = inode.dereference()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)
        with self.assertRaises(gdb.NotAvailableError):
            bdev = storage.inode_on_bdev(inode)

    def test_inode_on_bdev_poison_inode(self):
        inode = util.get_typed_pointer(self.poisonptr, self.inode_type)
        inode = inode.dereference()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)
        with self.assertRaises(gdb.NotAvailableError):
            bdev = storage.inode_on_bdev(inode)

    def test_inode_to_block_device_bdev_inode(self):
        inode = self.get_block_device_inode()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)
        bdev = storage.inode_to_block_device(inode)
        self.assertTrue(type(bdev) is gdb.Value)
        self.assertTrue(bdev.type == self.block_device_type)

    def test_inode_to_block_device_filesystem_inode(self):
        inode = self.get_filesystem_inode()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)

        with self.assertRaises(TypeError):
            bdev = storage.inode_to_block_device(inode)

    def test_inode_to_block_device_null_inode(self):
        inode = util.get_typed_pointer(self.nullptr, self.inode_type)
        inode = inode.dereference()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)

        with self.assertRaises(gdb.NotAvailableError):
            bdev = storage.inode_to_block_device(inode)

    def test_inode_to_block_device_poison_inode(self):
        inode = util.get_typed_pointer(self.poisonptr, self.inode_type)
        inode = inode.dereference()
        self.assertTrue(type(inode) is gdb.Value)
        self.assertTrue(inode.type == self.inode_type)

        with self.assertRaises(gdb.NotAvailableError):
            bdev = storage.inode_to_block_device(inode)

    def test_gendisk_name_disk(self):
        bdev = self.get_block_device()
        name = storage.gendisk_name(bdev['bd_disk'])
        self.assertTrue(type(name) is str)

    def test_gendisk_name_part(self):
        bdev = self.get_block_device()
        name = storage.gendisk_name(bdev['bd_part'])
        self.assertTrue(type(name) is str)

    def test_gendisk_name_disk_null_bdev(self):
        bdev = util.get_typed_pointer(self.nullptr, self.block_device_type)
        bdev = bdev.dereference()
        with self.assertRaises(gdb.NotAvailableError):
            name = storage.gendisk_name(bdev['bd_disk'])

    def test_gendisk_name_disk_poison_bdev(self):
        bdev = util.get_typed_pointer(self.poisonptr, self.block_device_type)
        bdev = bdev.dereference()
        with self.assertRaises(gdb.NotAvailableError):
            name = storage.gendisk_name(bdev['bd_disk'])

    def test_gendisk_to_dev(self):
        gendisk = self.get_gendisk()
        self.assertTrue(type(gendisk) is gdb.Value)
        self.assertTrue(gendisk.type == self.gendisk_type)

        dev = storage.gendisk_to_dev(gendisk)
        self.assertTrue(type(dev) is gdb.Value)
        self.assertTrue(dev.type == self.device_type)

    def test_part_to_dev(self):
        part = self.get_hd_struct()
        self.assertTrue(type(part) is gdb.Value)
        self.assertTrue(part.type == self.hd_struct_type)

        dev = storage.part_to_dev(part)
        self.assertTrue(type(dev) is gdb.Value)
        self.assertTrue(dev.type == self.device_type)

    def test_dev_to_gendisk(self):
        gendisk = self.get_gendisk()
        self.assertTrue(type(gendisk) is gdb.Value)
        self.assertTrue(gendisk.type == self.gendisk_type)

        dev = storage.gendisk_to_dev(gendisk)
        self.assertTrue(type(dev) is gdb.Value)
        self.assertTrue(dev.type == self.device_type)

        ngendisk = storage.dev_to_gendisk(dev)
        self.assertTrue(type(ngendisk) is gdb.Value)
        self.assertTrue(ngendisk.type == self.gendisk_type)
        self.assertTrue(gendisk == ngendisk)

    def test_dev_to_part(self):
        hd_struct = self.get_hd_struct()
        self.assertTrue(type(hd_struct) is gdb.Value)
        self.assertTrue(hd_struct.type == self.hd_struct_type)

        dev = storage.part_to_dev(hd_struct)
        self.assertTrue(type(dev) is gdb.Value)
        self.assertTrue(dev.type == self.device_type)

        nhd_struct = storage.dev_to_part(dev)
        self.assertTrue(type(nhd_struct) is gdb.Value)
        self.assertTrue(nhd_struct.type == self.hd_struct_type)
        self.assertTrue(hd_struct == nhd_struct)
