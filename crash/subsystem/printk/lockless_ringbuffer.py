# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Dict, Iterable, Any

import argparse
import sys
import gdb

from crash.util.symbols import Types, Symvals
from crash.exceptions import DelayedAttributeError
from crash.subsystem.printk import LogTypeException, LogInvalidOption

types = Types(['struct printk_info *',
               'struct prb_desc *',
               'struct prb_data_block *',
               'unsigned long',
               'char *'])

symvals = Symvals(['prb', 'clear_seq'])

# TODO: put to separate type
def atomic_long_read(val: gdb.Value) -> int:
    return int(val["counter"])

def read_null_end_string(buf: gdb.Value) -> str:
    ''' Read null-terminated string from a given buffer. '''
    text = buf.string(encoding='utf8', errors='replace')
    return text.partition('\0')[0]

class LogConsistencyException(Exception):
    pass

class DevPrintkInfo:
    ''' Kernel struct dev_printk_info '''
    subsystem: str
    device: str

    def __init__(self, info: gdb.Value) -> None:
        self.subsystem = read_null_end_string(info['subsystem'])
        self.device = read_null_end_string(info['device'])


class PrintkInfo:
    ''' Kernel struct printk_info '''
    seq: int			# sequence number
    ts_nsec: int		# timestamp in nanoseconds
    text_len: int	# length of text message
    facility: int	# syslog facility
    flags: int		# internal record flags
    level: int		# syslog level
    caller_id: int	# thread id or processor id
    dev_info: DevPrintkInfo

    def __init__(self, info: gdb.Value) -> None:
        self.seq = int(info['seq'])
        self.ts_nsec = int(info['ts_nsec'])
        self.text_len = int(info['text_len'])
        self.facility = int(info['facility'])
        self.flags = int(info['flags'])
        self.level = int(info['level'])
        self.caller_id = int(info['caller_id'])
        self.dev_info = DevPrintkInfo(info['dev_info'])


class PrbDataBlkLPos:
    ''' Kernel struct prb_data_blk_pos '''
    begin: int
    next: int

    def __init__(self, blk_lpos: gdb.Value) -> None:
        self.begin = int(blk_lpos['begin'])
        self.next = int(blk_lpos['next'])


class PrbDesc:
    ''' Kernel struct prb_desc '''
    state_var: int
    text_blk_lpos: PrbDataBlkLPos
    sv_shift: int
    sv_mask: int

    def __init__(self, desc: gdb.Value) -> None:
        self.state_var = atomic_long_read(desc['state_var'])
        self.text_blk_lpos = PrbDataBlkLPos(desc['text_blk_lpos'])

        sv_bits = types.unsigned_long_type.sizeof * 8
        self.sv_shift = sv_bits - 2
        self.sv_mask = 0x3 << self.sv_shift

    def desc_state(self) -> int:
        ''' Return state of the descriptor '''
        return (self.state_var & self.sv_mask) >> self.sv_shift

    def is_finalized(self):
        ''' Finalized desriptor points to a valid (deta) message '''
        return self.desc_state() == 0x2

    def is_reusable(self):
        '''
        Reusable descriptor still has a valid sequence number
        but the data are gone.
        '''
        return self.desc_state() == 0x3


class PrbDataBlock:
    ''' Kernel struct prb_data_block '''
    id: int
    data: gdb.Value

    def __init__(self, dr: gdb.Value) -> None:
        self.id = int(dr['id'])
        self.data = dr['data']

class PrbDataRing:
    ''' Kernel struct prb_data_ring '''
    size_bits: int
    data: gdb.Value
    lpos_mask: int

    def __init__(self, dr: gdb.Value) -> None:
        self.size_bits = int(dr['size_bits'])
        self.data = dr['data']

        self.lpos_mask = (1 << self.size_bits) - 1

    def get_data_block(self, blk_lpos: PrbDataBlkLPos) -> PrbDataBlock:
        ''' Return PrbDataBlock for the given blk_lpos '''
        begin_idx = blk_lpos.begin & self.lpos_mask
        blk_p = self.data.cast(types.char_p_type) + begin_idx
        return PrbDataBlock(blk_p.cast(types.prb_data_block_p_type))

    def get_text(self, blk_lpos: PrbDataBlkLPos, len: int) -> str:
        ''' return string stored at the given blk_lpos '''
        data_block = self.get_data_block(blk_lpos)
        return data_block.data.string(length=len)


class PrbDescRing:
    ''' Kernel struct prb_desc_ring '''
    count_bits: int
    descs: gdb.Value
    infos: gdb.Value
    head_id: int
    tail_id: int
    mask_id: int

    def __init__(self, dr: gdb.Value) -> None:
        self.count_bits = int(dr['count_bits'])
        self.descs = dr['descs']
        self.infos = dr['infos']
        self.head_id = atomic_long_read(dr['head_id'])
        self.tail_id = atomic_long_read(dr['tail_id'])
        self.mask_id = (1 << self.count_bits) - 1

    def get_idx(self, id: int) -> int:
        ''' Return index to the desc ring for the given id '''
        return id & self.mask_id

    def get_desc(self, id: int) -> PrbDesc:
        ''' Return prb_desc structure for the given id '''
        idx = self.get_idx(id)
        desc_p = (self.descs.cast(types.char_p_type) +
                  types.prb_desc_p_type.target().sizeof * idx)
        return PrbDesc(desc_p.cast(types.prb_desc_p_type))

    def get_info(self, id: int) -> PrintkInfo:
        ''' return printk_info structure for the given id '''
        idx = self.get_idx(id)
        info_p = (self.infos.cast(types.char_p_type) +
                  types.printk_info_p_type.target().sizeof * idx)
        return PrintkInfo(info_p.cast(types.printk_info_p_type))


class PrbRingBuffer:
    ''' Kernel struct prb_ring_buffer '''
    desc_ring: PrbDescRing
    data_ring: PrbDataRing

    def __init__(self, prb: gdb.Value) -> None:
        self.desc_ring = PrbDescRing(gdb.Value(prb['desc_ring']))
        self.data_ring = PrbDataRing(gdb.Value(prb['text_data_ring']))

    def is_valid_desc(self, desc: PrbDesc, info: PrintkInfo, seq: int) -> bool:
        ''' Does the descritor constains consistent values? '''
        if (not (desc.is_finalized() or desc.is_reusable())):
            return False
        # Must match the expected seq number. Otherwise is being updated.
        return (info.seq == seq)

    def first_seq(self) -> int:
        '''
        Get sequence number of the tail entry.
        '''

        # The lockless algorithm guarantees that the tail entry
        # always points to a descriptor in finalized or reusable state.
        # The only exception is when the tail is being moved
        # to the next entry, see prb_first_seq() in printk_ringbuffer.c
        #
        # As a result, the valid sequence number should be either in tail_id
        # or tail_id + 1 entry.
        for i in range(0, 1):
            id = self.desc_ring.tail_id + i
            desc = self.desc_ring.get_desc(id)

            if (desc.is_finalized() or desc.is_reusable()):
                info = self.desc_ring.get_info(id)
                return info.seq

        # Something went wrong. Do not continue with an invalid sequence number.
        raise LogConsistencyException('Can not find valid info in the tail descriptor')

    def show_msg(self, desc: PrbDesc, info: PrintkInfo,
                 args: argparse.Namespace) -> None:
        '''
        Show the message for the gived descriptor, printk info.
        The output is mofified by pylog parameters.
        '''

        timestamp = ''
        if not args.t:
            timestamp = ('[{:5d}.{:06d}] '
                         .format(info.ts_nsec // 1000000000,
                                 (info.ts_nsec % 1000000000) // 1000))

        level = ''
        if args.m:
            level = '<{:d}>'.format(info.level)

        text = self.data_ring.get_text(desc.text_blk_lpos, info.text_len)
        print('{}{}{}'.format(level,timestamp,text))

        if (args.d):
            # Only two dev_info values are supported at the moment
            if (len(info.dev_info.subsystem)):
                print('  SUBSYSTEM={}'.format(info.dev_info.subsystem))
            if (len(info.dev_info.device)):
                print('  DEVICE={}'.format(info.dev_info.device))

    def show_log(self, args: argparse.Namespace) -> None:
        """ Show the entire log """
        seq = self.first_seq()

        # Iterate over all entries with valid sequence number
        while True:
            desc = self.desc_ring.get_desc(seq)
            info = self.desc_ring.get_info(seq)
            if (not self.is_valid_desc(desc, info, seq)):
                break

            seq += 1

            # Sequence numbers are stored in separate ring buffer.
            # The descriptor ring might include valid sequence numbers
            # but the data might already be replaced.
            if (desc.is_reusable()):
                continue

            self.show_msg(desc, info, args)
        return

def lockless_rb_show(args: argparse.Namespace) -> None:
    """
    Try to show printk log stored in the lockless ringbuffer

    This type of ringbuffer has replaced the structured ring buffer
    in kernel-5.10.

    Raises:
         LogTypeException: The log is not in the lockless ringbuffer.
    """

    try:
        test = symvals.prb
    except DelayedAttributeError:
        raise LogTypeException('not lockless log') from None

    prb = PrbRingBuffer(symvals.prb)

    prb.show_log(args)
