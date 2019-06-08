# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
SUMMARY
-------

Select task by pid

::

  task <pid>

DESCRIPTION
-----------

This command selects the appropriate gdb thread using its Linux pid.

If no pid is specified, the current pid will be displayed.

EXAMPLES
--------

::
  task 1402
"""

import argparse

from crash.commands import Command, ArgumentParser
import crash.cache.tasks

import gdb

class TaskCommand(Command):
    """select task by pid"""

    def __init__(self, name: str) -> None:

        parser = ArgumentParser(prog=name)

        parser.add_argument('pid', type=int, nargs=argparse.REMAINDER)

        Command.__init__(self, name, parser)

    def execute(self, args: argparse.Namespace) -> None:
        try:
            if args.pid:
                thread = crash.cache.tasks.get_task(args.pid[0]).thread
            else:
                thread = gdb.selected_thread()

            gdb.execute("thread {}".format(thread.num))
        except KeyError:
            print("No such task with pid {}".format(args.pid[0]))

TaskCommand("task")
