#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import sys

from setuptools import setup, find_packages

setup(
    name = "crash",
    version = "0.1",
    packages = find_packages(exclude=['tests', 'kernel-tests']),
    package_data = {
        '' : [ "*.dist" "*.txt" ],
    },
    python_requires='>=3.6',

    install_requires = [ 'pyelftools', 'addrxlat' ],

    author = "Jeff Mahoney",
    author_email = "jeffm@suse.com",
    description = "Python Linux Kernel Crash dump forensic tools",
    license = "GPL v2 only",

)
