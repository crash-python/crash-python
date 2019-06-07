pycrash(1)
==========

NAME
----
pycrash - a Linux kernel crash dump debugger written in Python

SYNOPSIS
--------
*pycrash* [options] <path-to-vmlinux> <path-to-vmcore>

DESCRIPTION
-----------
The *pycrash* utility is a Linux kernel crash debugger written in Python.  It
improves upon the original crash tool by adding support for symbolic
backtraces and in that it is easily extensible by the user using a rich
python interface that offers semantic helpers for various subsystems.

In order to operate properly, full debuginfo is required for the kernel
image and all modules in use.  Without options specifying other paths,
the following defaults are used for locating the debuginfo and modules:

Kernel debuginfo:

* <path-to-vmlinux>.debug
* ./vmlinux-<kernel-version>.debug
* /usr/lib/debug/.build-id/<xx>/<build-id>.debug
* /usr/lib/debug/<path-to-vmlinux>.debug
* /usr/lib/debug/boot/vmlinux-<kernel-version>.debug
* /usr/lib/debug/boot/vmlinux-<kernel-version>

Module path:

* ./modules
* /lib/modules/<kernel-version>

Module debuginfo path:

* ./modules.debug
* /usr/lib/debug/.build-id/xx/<build-id>.debug
* /usr/lib/debug/lib/modules/<kernel-version>

The build-id and kernel-version fields are detected within the kernel
and modules and cannot be overridden.


OPTIONS
-------

Each of the following options may be specified multiple times.

``-r <dir> | --root <dir>``

    Use the specified directory as the root for all file searches.  When
    using properly configured .build-id symbolic links, this is the
    best method to use as the debuginfo will be loaded automatically via
    gdb without searching for filenames.  If this is the only option
    specified, the defaults documented above will be used relative to
    each root.

``-m <dir> | --modules <dir>``

    Use the specified directory to search for modules

``-d <dir> | --modules-debuginfo <dir>``

    Use the specified directory to search for module debuginfo

``-D <dir> | --vmlinux-debuginfo <dir>``

    Use the specified directory to search for vmlinux debuginfo

``-b <dir> | --build-dir <dir>``

    Use the specified directory as the root for all file searches.  This
    directory should be the root of a built kernel source tree.  This is
    shorthand for ``-r <dir> -m . -d . -D .`` and will override preceding
    options.

DEBUGGING OPTIONS:
------------------

``-v | --verbose``

    Enable verbose output for debugging the debugger

``--debug``

    Enable even noisier output for debugging the debugger

``--gdb``

    Run the embedded gdb underneath a separate gdb instance.  This is useful
    for debugging issues in gdb that are seen while running crash-python.

``--valgrind``

    Run the embedded gdb underneath valgrind.  This is useful
    for debugging memory leaks in gdb patches.

EXIT STATUS
-----------
*pycrash* returns a zero exit status if it succeeds.  Non zero is returned in
case of failure.

AVAILABILITY
------------
*pycrash* is part of crash-python.
Please refer to the GitHub repository at https://github.com/jeffmahoney/crash-python for more information.

SEE ALSO
--------
gdb(1)
libkdumpfile(7)
