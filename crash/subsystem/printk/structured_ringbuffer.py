# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Dict, Iterable, Any

import argparse

import gdb

from crash.util.symbols import Types, Symvals
from crash.exceptions import DelayedAttributeError
from crash.subsystem.printk import LogTypeException

types = Types(['struct printk_log *', 'char *'])
symvals = Symvals(['log_buf', 'log_buf_len', 'log_first_idx', 'log_next_idx',
                   'clear_seq', 'log_first_seq', 'log_next_seq'])


def log_from_idx(logbuf: gdb.Value, idx: int) -> Dict:
    msg = (logbuf + idx).cast(types.printk_log_p_type)

    try:
        textval = (msg.cast(types.char_p_type) +
                   types.printk_log_p_type.target().sizeof)
        text = textval.string(length=int(msg['text_len']))
    except UnicodeDecodeError as e:
        print(e)

    textlen = int(msg['text_len'])
    dictlen = int(msg['dict_len'])

    dictval = (msg.cast(types.char_p_type) +
               types.printk_log_p_type.target().sizeof + textlen)
    msgdict = dictval.string(length=dictlen)

    msglen = int(msg['len'])

    # A zero-length message means we wrap back to the beginning
    if msglen == 0:
        nextidx = 0
    else:
        nextidx = idx + msglen

    return {
        'text' : text[0:textlen],
        'timestamp' : int(msg['ts_nsec']),
        'level' : int(msg['level']),
        'next' : nextidx,
        'dict' : msgdict[0:dictlen],
    }

def get_log_msgs() -> Iterable[Dict[str, Any]]:
    try:
        idx = symvals.log_first_idx
    except DelayedAttributeError:
        raise LogTypeException('not structured log') from None

    if symvals.clear_seq < symvals.log_first_seq:
        # mypy seems to think the preceding clear_seq is fine but this
        # one isn't.  Derp.
        symvals.clear_seq = symvals.log_first_seq # type: ignore

    seq = symvals.clear_seq
    idx = symvals.log_first_idx

    while seq < symvals.log_next_seq:
        msg = log_from_idx(symvals.log_buf, idx)
        seq += 1
        idx = msg['next']
        yield msg

def structured_rb_show(args: argparse.Namespace) -> None:
    for msg in get_log_msgs():
        timestamp = ''
        if not args.t:
            usecs = int(msg['timestamp'])
            timestamp = ('[{:5d}.{:06d}] '
                         .format(usecs // 1000000000,
                                 (usecs % 1000000000) // 1000))

        level = ''
        if args.m:
            level = '<{:d}>'.format(msg['level'])

        for line in msg['text'].split('\n'):
            print('{}{}{}'.format(level, timestamp, line))

        if (args.d and msg['dict']):
            for entry in msg['dict'].split('\0'):
                print('  {}'.format(entry))
