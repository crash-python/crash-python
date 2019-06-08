#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import sys
import os
import fnmatch
import re

sys.path.insert(0, 'doc-source/mock')
sys.path.insert(0, 'mock')
import gdb

header = \
"""
Command Reference
=================

.. toctree::
    :titlesonly:

"""

def gen_command_docs(root: str) -> None:
    modules = list()
    print("*** Generating command docs")

    regex = re.compile(fnmatch.translate("[a-z]*.py"))
    for _root, dirs, files in os.walk(f"{root}/../crash/commands"):
        if '__pycache__' in _root:
            continue
        for filename in files:
            path = os.path.join(_root, filename)
            if regex.match(filename):
                mod = filename.replace(".py", "")
                modules.append(f"crash.commands.{mod}")

    old = set()

    try:
        os.mkdir(f"{root}/commands")
    except FileExistsError:
        pass

    print(f"Writing {root}/commands/commands.rst")
    cmdtoc = open(f"{root}/commands/commands.rst", "w")

    print(header, file=cmdtoc)

    print(f"** Generating docs for {modules}")

    for mod in modules:
        __import__(mod)

        new = set(gdb.commands)

        commands = new - old

        for command in commands:
            f = open(f"{root}/commands/{command}.rst", "w")
            print(f"``{command}``", file=f)
            print(f"----------------", file=f)
            print(f".. automodule:: {mod}", file=f)
            f.close()

        old = new

    for command in sorted(gdb.commands):
        print(f"    {command}", file=cmdtoc)

    cmdtoc.close()
