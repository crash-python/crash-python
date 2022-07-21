# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import argparse
import re

import gdb

from crash.util.symbols import Types, Symvals
from crash.subsystem.printk import LogTypeException, LogInvalidOption

types = Types(['char *'])
symvals = Symvals(['log_buf', 'log_buf_len'])

def plain_rb_filter(log: str, args: argparse.Namespace) -> str:
    lines = log.split('\n')
    if not args.m:
        newlog = []
        for line in lines:
            if not args.m:
                line = re.sub(r'^<[0-9]+>', '', line)
            if args.t:
                line = re.sub(r'^\[[0-9\. ]+\] ', '', line)
            newlog.append(line)
        lines = newlog

    return '\n'.join(lines)

def plain_rb_show(args: argparse.Namespace) -> None:
    if symvals.log_buf_len and symvals.log_buf:
        if args.d:
            raise LogInvalidOption("Unstructured logs don't offer key/value pair support")

        print(plain_rb_filter(symvals.log_buf.string('utf-8', 'replace'), args))
