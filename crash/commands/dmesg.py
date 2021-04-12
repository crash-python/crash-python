# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
SUMMARY
-------

Display system message buffer

::

  log [-tdm]
  dmesg [-tdm]

DESCRIPTION
-----------

This command dumps the kernel ``log_buf`` contents in chronological order.
The command supports the older log_buf formats, which may or may not contain a
timestamp inserted prior to each message, as well as the newer variable-length
record format, where the timestamp is contained in each log entry's header.


  -t  Display the message text without the timestamp.
  -d  Display the dictionary of key/value pair properties that are
      optionally appended to a message by the kernel's dev_printk()
      function; only applicable to the variable-length record format.
  -m  Display the message log level in brackets preceding each message.
      For the variable-length record format, the level will be displayed
      in hexadecimal, and depending upon the kernel version, also contains
      the facility or flags bits.

EXAMPLES
--------

Dump the kernel message buffer:

::

  py-crash> log
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

::

  py-crash> log -m
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

::

  py-crash> log
  [    0.467730] pci 0000:ff:02.0: [8086:2c10] type 00 class 0x060000
  [    0.467749] pci 0000:ff:02.1: [8086:2c11] type 00 class 0x060000
  [    0.467769] pci 0000:ff:02.4: [8086:2c14] type 00 class 0x060000
  [    0.467788] pci 0000:ff:02.5: [8086:2c15] type 00 class 0x060000
  [    0.467809] pci 0000:ff:03.0: [8086:2c18] type 00 class 0x060000
  [    0.467828] pci 0000:ff:03.1: [8086:2c19] type 00 class 0x060000
  ...

Display the same message text as above, without the timestamp data:

::

  py-crash> log -t
  pci 0000:ff:02.0: [8086:2c10] type 00 class 0x060000
  pci 0000:ff:02.1: [8086:2c11] type 00 class 0x060000
  pci 0000:ff:02.4: [8086:2c14] type 00 class 0x060000
  pci 0000:ff:02.5: [8086:2c15] type 00 class 0x060000
  pci 0000:ff:03.0: [8086:2c18] type 00 class 0x060000
  pci 0000:ff:03.1: [8086:2c19] type 00 class 0x060000
  ...

Display the same message text as above, with appended dictionary data:

::

  py-crash> log -td
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

from typing import Dict, Iterable, Any

import argparse

import gdb

from crash.commands import Command, ArgumentParser, CommandError
from crash.exceptions import DelayedAttributeError
from crash.subsystem.printk import LogTypeException, LogInvalidOption
from crash.subsystem.printk.lockless_ringbuffer import lockless_rb_show
from crash.subsystem.printk.structured_ringbuffer import structured_rb_show
from crash.subsystem.printk.plain_ringbuffer import plain_rb_show

class LogCommand(Command):
    """dump system message buffer"""

    def __init__(self, name: str) -> None:
        parser = ArgumentParser(prog=name)

        parser.add_argument('-t', action='store_true', default=False)
        parser.add_argument('-d', action='store_true', default=False)
        parser.add_argument('-m', action='store_true', default=False)

        Command.__init__(self, name, parser)

    def execute(self, args: argparse.Namespace) -> None:
        try:
            lockless_rb_show(args)
            return
        except LogTypeException:
            pass

        try:
            structured_rb_show(args)
            return
        except LogTypeException:
            pass

        try:
            plain_rb_show(args)
            return
        except LogTypeException:
            pass
        except LogInvalidOption as lio:
            raise CommandError(str(lio)) from lio

        print("Can't find valid log")

        print(args)

LogCommand('log')
LogCommand('dmesg')
