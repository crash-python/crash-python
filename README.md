This repository contains the python extensions for interacting
with Linux kernel crash dumps.

You'll need:
* [libkdumpfile](https://github.com/ptesarik/libkdumpfile)
* [gdb-python](https://github.com/jeffmahoney/gdb-python/tree/gdb-8.1-suse-target)

Packages for SUSE-created releases are available on the [Open Build Service](https://download.opensuse.org/repositories/home:/jeff_mahoney:/crash-python/).

Crash-python requires the following to run properly:
- The complete debuginfo for the kernel to be debug, including modules
- The ELF images for the kernel and all modules
- The vmcore dump image from the crashed system

To start:
`pycrash -d <dir to debuginfo and modules> <path-to-vmlinux> <path-to-vmcore>`

The `-d` option may be specified multiple times if multiple directories are
required.
