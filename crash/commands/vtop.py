#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import argparse
from crash.commands import CrashCommand, CrashCommandParser
from crash.addrxlat import addrxlat_context, addrxlat_system, addrxlat_is_non_auto
import addrxlat

class LinuxPGT(object):
    table_names = ( 'PTE', 'PMD', 'PUD', 'PGD' )

    def __init__(self, ctx, sys):
        self.context = ctx
        self.system = sys

    def begin(self, addr):
        meth = self.system.get_map(addrxlat.SYS_MAP_HW).search(addr)
        if meth == addrxlat.SYS_METH_NONE:
            meth = self.system.get_map(addrxlat.SYS_MAP_KV_PHYS).search(addr)
        if meth == addrxlat.SYS_METH_NONE:
            return False

        self.step = addrxlat.Step(self.context, self.system)
        self.step.meth = self.system.get_meth(meth)
        self.step.launch(addr)
        return True

    def next(self):
        if self.step.remain <= 1:
            return False

        level = self.step.remain - 1
        self.table = self.table_names[level - 1]
        self.ptr = self.step.base.copy()
        self.ptr.addr += self.step.idx[level] * self.step.elemsz

        self.note = ''
        try:
            self.step.step()
        except addrxlat.NotPresentError:
            self.note = ' (NOT PRESENT)'
            self.step.remain = 0
        return True

    def address(self):
        return '{:16x}'.format(self.ptr.addr)

    def value(self):
        return '{:x}{}'.format(self.step.raw, self.note)

class LinuxNonAutoPGT(LinuxPGT):
    def address(self):
        addr = super(LinuxNonAutoPGT, self).address() + ' [machine], '
        tmp = self.ptr.copy()
        try:
            tmp.conv(addrxlat.KPHYSADDR, self.context, self.system)
            return addr + '{:x} [phys]'.format(tmp.addr)
        except (addrxlat.NotPresentError, addrxlat.NoDataError):
            return addr + 'N/A'

class VTOPCommand(CrashCommand):
    """convert virtual address to physical

NAME
  vtop - virtual to physical

SYNOPSIS
  vtop [-c [pid | taskp]] [-u|-k] address ...

DESCRIPTION
  This command translates a user or kernel virtual address to its physical
  address.  Also displayed is the PTE translation, the vm_area_struct data
  for user virtual addresses, the mem_map page data associated with the
  physical page, and the swap location or file location if the page is
  not mapped.  The -u and -k options specify that the address is a user
  or kernel virtual address; -u and -k are not necessary on processors whose
  virtual addresses self-define themselves as user or kernel.  User addresses
  are translated with respect to the current context unless the -c option
  is used.  Kernel virtual addresses are translated using the swapper_pg_dir
  as the base page directory unless the -c option is used.

   -u                 The address is a user virtual address; only required
                      on processors with overlapping user and kernel virtual
                      address spaces.
   -k                 The address is a kernel virtual address; only required
                      on processors with overlapping user and kernel virtual
                      address spaces.
   -c [pid | taskp]   Translate the virtual address from the page directory
                      of the specified PID or hexadecimal task_struct pointer.
                      However, if this command is invoked from "foreach vtop",
                      the pid or taskp argument should NOT be entered; the
                      address will be translated using the page directory of
                      each task specified by "foreach".
   address            A hexadecimal user or kernel virtual address.

EXAMPLES
  Translate user virtual address 80b4000:

    crash> vtop 80b4000
    VIRTUAL   PHYSICAL
    80b4000   660f000

    PAGE DIRECTORY: c37f0000
      PGD: c37f0080 => e0d067
      PMD: c37f0080 => e0d067
      PTE: c0e0d2d0 => 660f067
     PAGE: 660f000

      PTE    PHYSICAL  FLAGS
    660f067   660f000  (PRESENT|RW|USER|ACCESSED|DIRTY)

      VMA      START      END      FLAGS  FILE
    c773daa0   80b4000   810c000    77

      PAGE    PHYSICAL   INODE     OFFSET  CNT FLAGS
    c0393258   660f000         0     17000  1  uptodate

  Translate kernel virtual address c806e000, first using swapper_pg_dir
  as the page directory base, and secondly, using the page table base
  of PID 1359:

    crash> vtop c806e000
    VIRTUAL   PHYSICAL
    c806e000  2216000

    PAGE DIRECTORY: c0101000
      PGD: c0101c80 => 94063
      PMD: c0101c80 => 94063
      PTE: c00941b8 => 2216063
     PAGE: 2216000

      PTE    PHYSICAL  FLAGS
    2216063   2216000  (PRESENT|RW|ACCESSED|DIRTY)

      PAGE    PHYSICAL   INODE     OFFSET  CNT FLAGS
    c02e9370   2216000         0         0  1

    crash> vtop -c 1359 c806e000
    VIRTUAL   PHYSICAL
    c806e000  2216000

    PAGE DIRECTORY: c5caf000
      PGD: c5cafc80 => 94063
      PMD: c5cafc80 => 94063
      PTE: c00941b8 => 2216063
     PAGE: 2216000

      PTE    PHYSICAL  FLAGS
    2216063   2216000  (PRESENT|RW|ACCESSED|DIRTY)

      PAGE    PHYSICAL   INODE     OFFSET  CNT FLAGS
    c02e9370   2216000         0         0  1

  Determine swap location of user virtual address 40104000:

    crash> vtop 40104000
    VIRTUAL   PHYSICAL
    40104000  (not mapped)

    PAGE DIRECTORY: c40d8000
      PGD: c40d8400 => 6bbe067
      PMD: c40d8400 => 6bbe067
      PTE: c6bbe410 => 58bc00

     PTE      SWAP     OFFSET
    58bc00  /dev/sda8   22716

      VMA      START      END     FLAGS  FILE
    c7200ae0  40104000  40b08000    73

    SWAP: /dev/sda8  OFFSET: 22716
    """

    def __init__(self):
        parser = CrashCommandParser(prog="vtop")

        group = parser.add_mutually_exclusive_group()
        group.add_argument('-u', action='store_true', default=False)
        group.add_argument('-k', action='store_true', default=False)

        parser.add_argument('-c', action='store_true', default=False)

        parser.add_argument('args', nargs=argparse.ONE_OR_MORE)

        parser.format_usage = lambda : \
        "vtop [-c [pid | taskp]] [-u|-k] address ...\n"

        super(VTOPCommand, self).__init__("vtop", parser)

    def execute(self, argv):
        ctx = addrxlat_context()
        sys = addrxlat_system()
        if addrxlat_is_non_auto():
            pgt = LinuxNonAutoPGT(ctx, sys)
        else:
            pgt = LinuxPGT(ctx, sys)

        for addr in argv.args:
            addr = int(addr, 16)
            fulladdr = addrxlat.FullAddress(addrxlat.KVADDR, addr)
            print('{:16}  {:16}'.format('VIRTUAL', 'PHYSICAL'))
            try:
                fulladdr.conv(addrxlat.KPHYSADDR, ctx, sys)
                phys = '{:x}'.format(fulladdr.addr)
            except addrxlat.BaseException:
                phys = '---'
            print('{:<16x}  {:<16}\n'.format(addr, phys))

            if pgt.begin(addr):
                while pgt.next():
                    print('{:>4}: {} => {}'.format(pgt.table, pgt.address(), pgt.value()))
                if pgt.step.remain:
                    pgt.ptr = pgt.step.base
                    print('PAGE: {}'.format(pgt.address()))
            else:
                print('NO TRANSLATION')

            print()

VTOPCommand()
