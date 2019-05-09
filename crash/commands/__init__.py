# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from crash.infra import CrashBaseClass

import gdb

import os
import glob
import importlib
import argparse

class CommandError(RuntimeError):
    pass

class CommandLineError(RuntimeError):
    pass

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CommandLineError(message)

class Command(CrashBaseClass, gdb.Command):
    commands = {}
    def __init__(self, name, parser=None):
        self.name = "py" + name
        if parser is None:
            parser = ArgumentParser(prog=self.name)
        elif not isinstance(parser, ArgumentParser):
            raise TypeError("parser must be ArgumentParser")

        nl = ""
        if self.__doc__[-1] != '\n':
            nl = "\n"
        parser.format_help = lambda: self.__doc__ + nl
        self.parser = parser
        self.commands[self.name] = self
        gdb.Command.__init__(self, self.name, gdb.COMMAND_USER)

    def invoke_uncaught(self, argstr, from_tty):
        argv = gdb.string_to_argv(argstr)
        args = self.parser.parse_args(argv)
        self.execute(args)

    def invoke(self, argstr, from_tty=False):
        try:
            self.invoke_uncaught(argstr, from_tty)
        except CommandError as e:
            print(f"{self.name}: {str(e)}")
        except CommandLineError as e:
            print(f"{self.name}: {str(e)}")
            self.parser.print_usage()
        except (SystemExit, KeyboardInterrupt):
            pass

    def execute(self, argv):
        raise NotImplementedError("Command should not be called directly")

def discover():
    modules = glob.glob(os.path.dirname(__file__)+"/[A-Za-z]*.py")
    __all__ = [os.path.basename(f)[:-3] for f in modules]

    mods = __all__
    for mod in mods:
        x = importlib.import_module("crash.commands.{}".format(mod))
