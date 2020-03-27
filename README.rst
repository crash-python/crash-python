crash-python
============

.. start-introduction

crash-python is a semantic debugger for the Linux kernel.  It is meant to
feel familiar for users of the classic
`crash <https://github.com/crash-utility/crash.git>`_ debugger but allows
much more powerful symbolic access to crash dumps as well as enabling an API for
writing ad-hoc extensions, commands, and analysis scripts.

.. code-block:: bash
	
    $ pycrash vmlinux-4.12.14-150.14-default.gz vmcore

    crash-python initializing...
    Loading tasks.... done. (170 tasks total)
    Loading modules for 4.12.14-150.14-default.... done. (78 loaded)
    [Switching to thread 170 (pid 27032)]
    #0  sysrq_handle_crash (key=99) at ../drivers/tty/sysrq.c:146
    146		*killer = 1;
    Backtrace from crashing task (PID 27032):
    #0  0xffffffffaa4b3682 in sysrq_handle_crash (key=99)
        at ../drivers/tty/sysrq.c:146
    #1  0xffffffffaa4b3d34 in __handle_sysrq (key=99, check_mask=false)
        at ../drivers/tty/sysrq.c:559
    #2  0xffffffffaa4b41eb in write_sysrq_trigger
        (file=<optimized out>, buf=<optimized out>, count=18446628512242465728, ppos=<optimized out>) at ../drivers/tty/sysrq.c:1105
    #3  0xffffffffaa2b95b0 in proc_reg_write
        (file=<optimized out>, buf=<optimized out>, count=<optimized out>, ppos=<optimized out>) at ../fs/proc/inode.c:230
    #4  0xffffffffaa246696 in __vfs_write
        (file=0x63 <irq_stack_union+99>, p=<optimized out>, count=<optimized out>, pos=0xffffa53fc0c5ff08) at ../fs/read_write.c:508
    #5  0xffffffffaa247c2d in vfs_write
        (file=0xffff96e5a9a24c00, buf=0x560dc6656220 <error: Cannot access memory at address 0x560dc6656220>, count=<optimized out>, pos=0xffffa53fc0c5ff08)
        at ../fs/read_write.c:558
    #6  0xffffffffaa249112 in SYSC_write
        (count=<optimized out>, buf=<optimized out>, fd=<optimized out>)
        at ../fs/read_write.c:605
    #7  0xffffffffaa249112 in SyS_write
        (fd=<optimized out>, buf=94617163096608, count=2) at ../fs/read_write.c:597
    #8  0xffffffffaa003ae4 in do_syscall_64 (regs=0x63 <irq_stack_union+99>)
        at ../arch/x86/entry/common.c:284
    #9  0xffffffffaa80009a in entry_SYSCALL_64 ()
        at ../arch/x86/entry/entry_64.S:236
    The 'pyhelp' command will list the command extensions.
    py-crash>
    py-crash> print *(struct file *)0xffff96e5a9a24c00
    $1 = {
      f_u = {
        fu_llist = {
          next = 0x0 <irq_stack_union>
        },
        fu_rcuhead = {
          next = 0x0 <irq_stack_union>,
          func = 0x0 <irq_stack_union>
        }
      },
      f_path = {
        mnt = 0xffff96e5b02d23a0,
        dentry = 0xffff96e4b65b06c0
      },
      f_inode = 0xffff96e5ad464578,
      f_op = 0xffffffffaac4d940 <proc_reg_file_ops_no_compat>,
      f_lock = {
        {
          rlock = {
            raw_lock = {
              val = {
                counter = 0
              }
            }
          }
        }
      },
      f_write_hint = WRITE_LIFE_NOT_SET,
      [...]

Full documentation can be found at `crash-python.readthedocs.io
<https://crash-python.readthedocs.io/en/latest/>`_.

.. end-introduction

Installation
------------

.. start-installation

`Crash-python <https://github.com/crash-python/crash-python>`_ is on `GitHub <https://github.com>`_.

It requires the following components to work successfully:

- `Python <https://python.org/>`_ 3.6 or newer
- `pyelftools <https://github.com/eliben/pyelftools>`_
- `libkdumpfile <https://github.com/ptesarik/libkdumpfile>`_
- `GDB <https://github.com/crash-python/gdb-python/tree/gdb-9.1-target>`_ with python extensions and built with Python 3.6 or newer.

If you are using a SUSE or openSUSE release, pre-built packages are available on the `Open Build Service <https://download.opensuse.org/repositories/home:/jeff_mahoney:/crash-python/>`_.

.. end-installation

Quick start
-----------

.. start-quick-start

Crash-python requires the following to run properly:

- The complete debuginfo for the kernel to be debugged, including modules
- The ELF images for the kernel and all modules
- The vmcore dump image from the crashed system

To start:

.. code-block:: bash

    $ pycrash [options] <path-to-vmlinux> <path-to-vmcore>

Since different systems and users place these files in different locations, there are number of command-line options to locate them. On a typical SUSE system, if you have the kernel-default and kernel-default-debuginfo packages installed, you will not need to provide any additional options.

If you have expanded the RPMs separately into a different directory, you can start with:

.. code-block:: bash

    $ pycrash -r /path/to/root <path-to-vmlinux> <path-to-vmcore>

If you’re debugging a kernel that you built from a source tree directly and installed using make INSTALL_MOD_STRIP=1 modules_install install, you can specify your build directory as a source for debuginfo:

.. code-block:: bash

    $ pycrash -b /path/to/build/dir <path-to-vmlinux> <path-to-vmcore>

The full options are documented with:

.. code-block:: bash

    $ pycrash --help

.. end-quick-start




License:
--------

.. start-license

Copyright 2016-2019 Jeff Mahoney, `SUSE <https://www.suse.com/>`_.

crash-python is licensed under the `GPLv2 <https://www.gnu.org/licenses/gpl-2.0.en.html>`_.

.. end-license
