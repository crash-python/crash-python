# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import gdb
from crash.commands import CrashCommand, CrashCommandParser
import crash.cache.tasks
import argparse

class TaskCommand(CrashCommand):
    """select task by pid

NAME
  task - select task by pid

SYNOPSIS
  task <pid>

DESCRIPTION
  This command selects the appropriate gdb thread using its Linux pid.

EXAMPLES
    task 1402
    """
    def __init__(self, name):

        parser = CrashCommandParser(prog=name)

        parser.add_argument('pid', type=int, nargs=1)

        parser.format_usage = lambda: "thread <pid>\n"
        CrashCommand.__init__(self, name, parser)

    def execute(self, args):
        try:
            thread = crash.cache.tasks.get_task(args.pid[0]).thread
            gdb.execute("thread {}".format(thread.num))
        except KeyError:
            print("No such task with pid {}".format(args.pid[0]))

TaskCommand("task")
