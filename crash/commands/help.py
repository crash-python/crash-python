# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
SUMMARY
-------

Display help for crash commands

::

  help [command]

DESCRIPTION
-----------

This command displays help text for crash commands.  When used alone,
it provides a list of commands.  When an argument is specified, the help
text for that command will be printed.
"""

import argparse

from crash.commands import Command, CommandError, ArgumentParser

class HelpCommand(Command):
    """ this command"""

    def __init__(self) -> None:
        parser = ArgumentParser(prog="help")
        parser.add_argument('args', nargs=argparse.REMAINDER)
        super().__init__('help', parser)

    def execute(self, args: argparse.Namespace) -> None:
        if not args.args:
            print("Available commands:")
            for cmd in sorted(self._commands):
                summary = None
                doc = self._commands[cmd].__doc__
                if doc:
                    summary = doc.strip()
                if not summary:
                    summary = "no help text provided"
                print("{:<15} - {}".format(cmd, summary))
        else:
            for cmd in args.args:
                try:
                    text = self._commands[cmd].format_help().strip()
                except KeyError:
                    raise CommandError("No such command `{}'".format(cmd)) from None
                if text is None:
                    print("No help text available.")
                else:
                    print(text)

HelpCommand()
