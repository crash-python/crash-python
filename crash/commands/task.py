# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from crash.commands import Command, ArgumentParser
import crash.cache.tasks
import argparse

class TaskCommand(Command):
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

        parser = ArgumentParser(prog=name)

        parser.add_argument('pid', type=int, nargs=argparse.REMAINDER)

        parser.format_usage = lambda: "thread <pid>\n"
        Command.__init__(self, name, parser)

    def execute(self, args):
        try:
            if args.pid:
                thread = crash.cache.tasks.get_task(args.pid[0]).thread
            else:
                thread = gdb.selected_thread()

            gdb.execute("thread {}".format(thread.num))
        except KeyError:
            print("No such task with pid {}".format(args.pid[0]))

TaskCommand("task")
