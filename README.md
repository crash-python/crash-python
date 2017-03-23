This repository contains the python extensions for interacting
with Linux kernel crash dumps.

You'll need:
* libkdumpfile: https://github.com/ptesarik/libkdumpfile
* gdb-python: https://github.com/jeffmahoney/gdb-python/tree/python-working-target


Install on Tumbleweed
=====================

To install on OpenSuse Tumbleweed you can do the following:

zypper ar http://download.opensuse.org/repositories/home:/jeff_mahoney:/crash-python/openSUSE_Tumbleweed/home:jeff_mahoney:crash-python.repo
zypper refresh
zypper install crash-python

If installing crash-python from source, be sure to uninstall the respective
rpm package.

Kenrel package requirements
===========================

You will need the debuginfo kernel package for the kenrel you are debugging
the vmcore for, so for instance if debugging kernel-default-3.0.101-0.47.90.1.x86_64
you will want to also install kernel-default-debuginfo-3.0.101-0.47.90.1.x86_64.

Usage
=====

You may want to consider using the script provided in crash-python to start off:

~/path-to/crash.sh vmlinux.gz vmcore

Contrary to crash, crash-python commands are prefixed with py, to see the
list of available commands:

pyhelp

If you just run help you are interacting with gdb directly.

Contrib
=======

Right now piping is not supported, this will require some modifications on
gdb, so for now the best way to use crash-python will be through python
scripts. Examples are provided in contrib, but note that these are tuned per
user. You may need to modify these per use case.

Contrib use examples
--------------------

### btrfs mounted filesystems

To list mounted btrfs filesystems:

source /home/user/crash-python/contrib/lsbtrfs-cmd.py

pyhelp  should now show the pylsbtrfs command available. To run this just
run:

pylsbtrfs

### xfs mounted filesystems
To list mounted xfs filesystems:

source /home/user/crash-python/contrib/lsxfs-cmd.py
pylsxfs
