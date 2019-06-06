# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from typing import Dict, Any

import os
import glob
import importlib
import argparse

from crash.exceptions import DelayedAttributeError, ArgumentTypeError

import gdb

class CommandError(RuntimeError):
    pass

class CommandLineError(RuntimeError):
    pass

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        raise CommandLineError(message)

    def format_help(self) -> str:
        if self.__doc__ is None:
            raise NotImplementedError("This command does not have help text")
        return self.__doc__.strip() + "\n"

class Command(gdb.Command):
    commands: Dict[str, gdb.Command] = dict()
    def __init__(self, name: str, parser: ArgumentParser = None) -> None:
        self.name = "py" + name
        if parser is None:
            parser = ArgumentParser(prog=self.name)
        elif not isinstance(parser, ArgumentParser):
            raise ArgumentTypeError('parser', parser, ArgumentParser)

        self.parser = parser
        self.commands[self.name] = self
        gdb.Command.__init__(self, self.name, gdb.COMMAND_USER)

    def format_help(self) -> str:
        return self.parser.format_help()

    # pylint: disable=unused-argument
    def invoke_uncaught(self, argstr: str, from_tty: bool = False) -> None:
        argv = gdb.string_to_argv(argstr)
        args = self.parser.parse_args(argv)
        self.execute(args)

    def invoke(self, argstr: str, from_tty: bool = False) -> None:
        try:
            self.invoke_uncaught(argstr, from_tty)
        except CommandError as e:
            print(f"{self.name}: {str(e)}")
        except CommandLineError as e:
            print(f"{self.name}: {str(e)}")
            self.parser.print_usage()
        except DelayedAttributeError as e:
            print(f"{self.name}: command unavailable, {str(e)}")
        except (SystemExit, KeyboardInterrupt):
            pass

    def execute(self, args: argparse.Namespace) -> None:
        raise NotImplementedError("Command should not be called directly")

def discover() -> None:
    modules = glob.glob(os.path.dirname(__file__)+"/[A-Za-z]*.py")
    __all__ = [os.path.basename(f)[:-3] for f in modules]

    mods = __all__
    for mod in mods:
        # pylint: disable=unused-variable
        x = importlib.import_module("crash.commands.{}".format(mod))
