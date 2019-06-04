# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import argparse

from crash.commands import Command, CommandError, ArgumentParser

class _Parser(ArgumentParser):
    """
    NAME
      help - display help for crash commands

    SYNOPSIS
      help [command]

    DESCRIPTION
      This command displays help text for crash commands.  When used alone,
      it provides a list of commands.  When an argument is specified, the help
      text for that command will be printed.
    """

class HelpCommand(Command):
    """ this command"""

    def __init__(self) -> None:
        parser = _Parser(prog="help")
        parser.add_argument('args', nargs=argparse.REMAINDER)
        super().__init__('help', parser)

    def execute(self, argv: argparse.Namespace) -> None:
        if not argv.args:
            print("Available commands:")
            for cmd in sorted(self.commands):
                summary = self.commands[cmd].__doc__.strip()
                if not summary:
                    summary = "no help text provided"
                print("{:<15} - {}".format(cmd, summary))
        else:
            for cmd in argv.args:
                try:
                    text = self.commands[cmd].format_help().strip()
                except KeyError:
                    raise CommandError("No such command `{}'".format(cmd))
                if text is None:
                    print("No help text available.")
                else:
                    print(text)

HelpCommand()
