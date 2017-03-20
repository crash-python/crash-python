#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

import gdb
from crash.commands import CrashCommand
import crash.cache.tasks
import argparse

class ThreadCommand(CrashCommand):
    """select thread by pid

NAME
  thread - select thread by pid

SYNOPSIS
  thread <pid>

DESCRIPTION
  This command selects the appropriate gdb thread using its Linux pid.

EXAMPLES
    pid 1
    """
    def __init__(self, name):

        parser = argparse.ArgumentParser(prog=name)

        parser.add_argument('pid', type=int, nargs=1)

        parser.format_usage = lambda : "thread <pid>\n"
        CrashCommand.__init__(self, name, parser)

    def execute(self, args):
        try:
            thread = crash.cache.tasks.get_task(args.pid[0]).thread
            gdb.execute("thread {}".format(thread.num))
        except KeyError as e:
            print("No such task with pid {}".format(args.pid[0]))
#        for thread in gdb.selected_inferior().threads():
#            if thread.info.task_struct['pid'] == args.pid[0]:
#                gdb.execute("thread {}".format(thread.num))
#                return

#        print("Couldn't find thread for pid {}".format(args.pid[0]))

ThreadCommand("thread")
