# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import argparse
from crash.commands import Command, ArgumentParser

class HelpCommand(Command):
    """ this command

NAME
  help - display help for crash commands

SYNOPSIS
  help [command]

DESCRIPTION
  This command displays help text for crash commands.  When used alone,
  it provides a list of commands.  When an argument is specified, the help
  text for that command will be printed.
"""

    def __init__(self):
        parser = ArgumentParser(prog="help")
        parser.add_argument('args', nargs=argparse.REMAINDER)
        super().__init__('help', parser)

    def execute(self, argv):
        if not argv.args:
            print("Available commands:")
            for cmd in sorted(self.commands):
                text = self.commands[cmd].__doc__
                if text:
                    summary = text.split('\n')[0].strip()
                else:
                    summary = "no help text provided"
                print("{:<15} - {}".format(cmd, summary))
        else:
            for cmd in argv.args:
                try:
                    text = self.commands[cmd].__doc__
                    if text is None:
                        print("No help text available.")
                    f = text.find("")
                    if f == -1:
                        print(text)
                    else:
                        print(text[f+1:])
                except KeyError:
                    print("No such command `{}'".format(cmd))

HelpCommand()
