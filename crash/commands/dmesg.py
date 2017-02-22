#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.commands import CrashCommand
from crash.types.util import safe_get_symbol_value as get_value
import argparse
import re

char = gdb.lookup_type('char')
charp = char.pointer()

class LogTypeException(Exception):
    pass

class LogInvalidOption(Exception):
    pass

class LogCommand(CrashCommand):
    """dump system message buffer

NAME
  log - dump system message buffer

SYNOPSIS
  log [-tdm]

DESCRIPTION
  This command dumps the kernel log_buf contents in chronological order.  The
  command supports the older log_buf formats, which may or may not contain a
  timestamp inserted prior to each message, as well as the newer variable-length
  record format, where the timestamp is contained in each log entry's header.

    -t  Display the message text without the timestamp.
    -d  Display the dictionary of key/value pair properties that are optionally
        appended to a message by the kernel's dev_printk() function; only
        applicable to the variable-length record format.
    -m  Display the message log level in brackets preceding each message.  For
        the variable-length record format, the level will be displayed in
        hexadecimal, and depending upon the kernel version, also contains the
        facility or flags bits.


EXAMPLES
  Dump the kernel message buffer:

    crash> log
    Linux version 2.2.5-15smp (root@mclinux1) (gcc version egcs-2.91.66 19990
    314/Linux (egcs-1.1.2 release)) #1 SMP Thu Aug 26 11:04:37 EDT 1999
    Intel MultiProcessor Specification v1.4
        Virtual Wire compatibility mode.
    OEM ID: DELL     Product ID: WS 410       APIC at: 0xFEE00000
    Processor #0 Pentium(tm) Pro APIC version 17
    Processor #1 Pentium(tm) Pro APIC version 17
    I/O APIC #2 Version 17 at 0xFEC00000.
    Processors: 2
    mapped APIC to ffffe000 (fee00000)
    mapped IOAPIC to ffffd000 (fec00000)
    Detected 447696347 Hz processor.
    Console: colour VGA+ 80x25
    Calibrating delay loop... 445.64 BogoMIPS
    ...
      8K byte-wide RAM 5:3 Rx:Tx split, autoselect/Autonegotiate interface.
      MII transceiver found at address 24, status 782d.
      Enabling bus-master transmits and whole-frame receives.
    Installing knfsd (copyright (C) 1996 okir@monad.swb.de).
    nfsd_init: initialized fhcache, entries=256
    ...

  Do the same thing, but also show the log level preceding each message:

    crash> log -m
    <4>Linux version 2.2.5-15smp (root@mclinux1) (gcc version egcs-2.91.66 19990
    314/Linux (egcs-1.1.2 release)) #1 SMP Thu Aug 26 11:04:37 EDT 1999
    <4>Intel MultiProcessor Specification v1.4
    <4>    Virtual Wire compatibility mode.
    <4>OEM ID: DELL     Product ID: WS 410       APIC at: 0xFEE00000
    <4>Processor #0 Pentium(tm) Pro APIC version 17
    <4>Processor #1 Pentium(tm) Pro APIC version 17
    <4>I/O APIC #2 Version 17 at 0xFEC00000.
    <4>Processors: 2
    <4>mapped APIC to ffffe000 (fee00000)
    <4>mapped IOAPIC to ffffd000 (fec00000)
    <4>Detected 447696347 Hz processor.
    <4>Console: colour VGA+ 80x25
    <4>Calibrating delay loop... 445.64 BogoMIPS
    ...
    <6>  8K byte-wide RAM 5:3 Rx:Tx split, autoselect/Autonegotiate interface.
    <6>  MII transceiver found at address 24, status 782d.
    <6>  Enabling bus-master transmits and whole-frame receives.
    <6>Installing knfsd (copyright (C) 1996 okir@monad.swb.de).
    <7>nfsd_init: initialized fhcache, entries=256
    ...

  On a system with the variable-length record format, and whose log_buf has been
  filled and wrapped around, display the log with timestamp data:

    crash> log
    [    0.467730] pci 0000:ff:02.0: [8086:2c10] type 00 class 0x060000
    [    0.467749] pci 0000:ff:02.1: [8086:2c11] type 00 class 0x060000
    [    0.467769] pci 0000:ff:02.4: [8086:2c14] type 00 class 0x060000
    [    0.467788] pci 0000:ff:02.5: [8086:2c15] type 00 class 0x060000
    [    0.467809] pci 0000:ff:03.0: [8086:2c18] type 00 class 0x060000
    [    0.467828] pci 0000:ff:03.1: [8086:2c19] type 00 class 0x060000
    ...

  Display the same message text as above, without the timestamp data:

    crash> log -t
    pci 0000:ff:02.0: [8086:2c10] type 00 class 0x060000
    pci 0000:ff:02.1: [8086:2c11] type 00 class 0x060000
    pci 0000:ff:02.4: [8086:2c14] type 00 class 0x060000
    pci 0000:ff:02.5: [8086:2c15] type 00 class 0x060000
    pci 0000:ff:03.0: [8086:2c18] type 00 class 0x060000
    pci 0000:ff:03.1: [8086:2c19] type 00 class 0x060000
    ...

  Display the same message text as above, with appended dictionary data:

    crash> log -td
    pci 0000:ff:02.0: [8086:2c10] type 00 class 0x060000
    SUBSYSTEM=pci
    DEVICE=+pci:0000:ff:02.0
    pci 0000:ff:02.1: [8086:2c11] type 00 class 0x060000
    SUBSYSTEM=pci
    DEVICE=+pci:0000:ff:02.1
    pci 0000:ff:02.4: [8086:2c14] type 00 class 0x060000
    SUBSYSTEM=pci
    DEVICE=+pci:0000:ff:02.4
    pci 0000:ff:02.5: [8086:2c15] type 00 class 0x060000
    SUBSYSTEM=pci
    DEVICE=+pci:0000:ff:02.5
    pci 0000:ff:03.0: [8086:2c18] type 00 class 0x060000
    SUBSYSTEM=pci
    DEVICE=+pci:0000:ff:03.0
    pci 0000:ff:03.1: [8086:2c19] type 00 class 0x060000
    SUBSYSTEM=pci
    DEVICE=+pci:0000:ff:03.1
    ...

    """
    def __init__(self, name):

        parser = argparse.ArgumentParser(prog=name)

        parser.add_argument('-t', action='store_true', default=False)
        parser.add_argument('-d', action='store_true', default=False)
        parser.add_argument('-m', action='store_true', default=False)

        parser.format_usage = lambda : "log [-tdm]\n"
        CrashCommand.__init__(self, name, parser)

        self.printk_log_type = None
        try:
            printk_log = gdb.lookup_type('struct printk_log')
            if printk_log:
                self.printk_log_type = printk_log.pointer()
        except gdb.error as e:
            pass

    def filter_unstructured_log(self, log, args):
        lines = log.split('\n')
        if not args.m:
            newlog = []
            for line in lines:
                if not args.m:
                    line = re.sub("^<[0-9]+>", "", line)
                if args.t:
                    line = re.sub("^\[[0-9\. ]+\] ", "", line)
                newlog.append(line)
            lines = newlog

        return "\n".join(lines)

    def log_from_idx(self, logbuf, idx, dict_needed=False):
        logbuf = logbuf.address.dereference()
        msg = (logbuf + idx).cast(self.printk_log_type)

        try:
            textval = msg.cast(charp) + self.printk_log_type.target().sizeof
            text = textval.string(length=msg['text_len'])
        except UnicodeDecodeError as e:
            print (e)

        msglen = int(msg['len'])

        # A zero-length message means we wrap back to the beginning
        if msglen == 0:
            nextidx = 0
        else:
            nextidx = idx + msglen

        textlen = int(msg['text_len'])

        msgdict = {
            'text' : text[0:textlen],
            'timestamp' : int(msg['ts_nsec']),
            'level' : int(msg['level']),
            'next' : nextidx,
            'dict' : [],
        }

        if dict_needed:
            dict_len = int(msg['dict_len'])
            d = msg.cast(charp) + self.printk_log_type.target().sizeof + textlen
            s = ""

            for i in range(0,dict_len):
                if d[i]:
                    s += chr(d[i])
                else:
                    msgdict['dict'].append(s)
                    s = ""

            if s != "":
                msgdict['dict'].append(s)
        return msgdict

    def get_log_msgs(self, dict_needed=False):
        first_idx = get_value('log_first_idx')
        next_idx = get_value("log_next_idx")
        clear_seq = get_value('clear_seq')
        first_seq = get_value('log_first_seq')
        next_seq = get_value('log_next_seq')
        logbuf = get_value("log_buf")

        if first_idx == None or next_idx == None:
            raise LogTypeException("not structured log")

        if clear_seq < first_seq:
            clear_seq = first_seq


        seq = clear_seq
        idx = first_idx

        while seq < next_seq:
            msg = self.log_from_idx(logbuf, idx, dict_needed)
            seq += 1
            idx = msg['next']
            yield(msg)

    def handle_structured_log(self, args):
        for msg in self.get_log_msgs(args.d):
            timestamp = ""
            if not args.t:
                timestamp = "[%5lu.%06lu] " % \
                            (msg['timestamp'] / 1000000000,
                            (msg['timestamp'] % 1000000000) / 1000)
            level = ""
            if args.m:
                level = "<%d>" % msg['level']

            for line in msg['text'].split('\n'):
                print(("%s%s%s" % (level, timestamp, line)))

            for d in msg['dict']:
                print(("%15s%s" % ("", d.encode('string_escape'))))

    def handle_logbuf(self, args):

        log_buf_len = get_value("log_buf_len")
        log_buf = get_value("log_buf")

        if log_buf_len and log_buf:
            if (args.d):
                raise LogInvalidOption("Unstructured logs don't offer key/value pair support")
            print((self.filter_unstructured_log(log_buf.string(), args)))

    def execute(self, args):
        try:
            self.handle_structured_log(args)
            return
        except LogTypeException as lte:
            pass

        try:
            self.handle_logbuf(args)
            return
        except LogTypeException as lte:
            pass
        except LogInvalidOption as lio:
            raise gdb.GdbError(str(lio))

        print ("Can't find valid log")

        print (args)

LogCommand("log")
LogCommand("dmesg")
