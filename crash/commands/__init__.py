# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
"""
The crash.commands module is the interface for implementing commands
in crash-python.

The only mandatory part of implementing a command is to derive a class
from :class:`.Command`, implement the :meth:`.Command.execute` method,
and instantiate it.  If the command should have multiple aliases,
accept a name in the constructor and instantiate it multiple times.

Optional extensions:

- Adding a parser (derived from :class:`.ArgumentParser`) that parses
  arguments.  If not provided, an empty parser will be used.
- Adding a module docstring to be used as help text.  If not provided,
  the argparse generic help text will be used instead.

The module docstring will be placed automatically in the command reference
section of the user guide and will also be converted into plaintext help
for use in command execution.  It should be in `reStructuredText
<https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_
format.

Example:

::

    \"\"\"
    NAME
    ----

      helloworld

    SYNOPSYS
    --------

      ``helloworld`` -- a command that prints hello world
    \"\"\"

    import crash.commands

    class HelloWorld(crash.commands.Command):
        def __init__(self) -> None:
            parser = crash.commands.ArgumentParser(prog='helloworld')

            super().__init__('helloworld', parser)

        def execute(self, args: argparse.Namespace) -> None:
            print("hello world")

    HelloWorld()
"""

from typing import Dict, Any, Optional, Tuple

import os
import glob
import importlib
import argparse

import gdb

from crash.exceptions import DelayedAttributeError, ArgumentTypeError

class CommandError(RuntimeError):
    """An error occured while executing this command"""

class CommandLineError(RuntimeError):
    """An error occured while handling the command line for this command"""

class ArgumentParser(argparse.ArgumentParser):
    """
    A simple extension to :class:`argparse.ArgumentParser` that:

    - Requires a command name be set
    - Loads help text automatically from files
    - Handles errors by raising :obj:`.CommandLineError`

    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        if not self.prog:
            raise CommandError("Cannot build command with no name")

    def error(self, message: str) -> Any:
        """
        An error callback that raises the :obj:`CommandLineError` exception.
        """
        raise CommandLineError(message)

    def format_help(self) -> str:
        """
        A help formatter that loads the parsed rST documentation from disk
        or returns the generic help text otherwise.
        """
        try:
            path = os.path.join(os.environ['CRASH_PYTHON_HELP'], 'commands',
                                f"{self.prog}.txt")
            f = open(path)
            helptext = f.read()
            f.close()
        except (KeyError, FileNotFoundError):
            helptext = "Could not locate help file.\n"
            helptext += "Generic help text follows.\n\n"
            helptext += super().format_help()

        return helptext

    @staticmethod
    def address(v: str) -> int:
        return int(v, 16)

class Command(gdb.Command):
    """
    The Command class is the starting point for implementing a new command.

    The :meth:`.Command.execute` method will be invoked when the user
    invokes the command.

    Once the constructor returns, the command will be registered with
    ``gdb`` and the command will be available for use.

    Args:
        name: The name of the command.  The string ``py`` will be prefixed
            to it.
        parser: The parser to use to handle the arguments.  It must be derived
            from the :class:`.ArgumentParser` class.

    Raises:
        ArgumentTypeError: The parser is not derived from
            :class:`.ArgumentParser`.

    """
    _commands: Dict[str, 'Command'] = dict()
    def __init__(self, name: str, parser: ArgumentParser = None) -> None:
        """
        """
        self.name = "py" + name
        if parser is None:
            parser = ArgumentParser(prog=self.name)
        elif not isinstance(parser, ArgumentParser):
            raise ArgumentTypeError('parser', parser, ArgumentParser)

        self._parser = parser
        self._commands[self.name] = self
        gdb.Command.__init__(self, self.name, gdb.COMMAND_USER)

    def format_help(self) -> str:
        """
        Used by the :mod:`.help` module, it delegates the help formatting
        to the parser object.
        """
        return self._parser.format_help()

    # pylint: disable=unused-argument
    def invoke_uncaught(self, argstr: str, from_tty: bool = False) -> None:
        """
        Invokes the command directly and does not catch exceptions.

        This is used mainly for unit testing to ensure proper exceptions
        are raised.

        Unless you are doing something special, see :meth:`execute` instead.

        Args:
            argstr: The command arguments
            from_tty (default=False): Whether the command was invoked from a
                tty.
        """
        argv = gdb.string_to_argv(argstr)
        args = self._parser.parse_args(argv)
        self.execute(args)

    def invoke(self, argstr: str, from_tty: bool = False) -> None:
        """
        Invokes the command directly and translates exceptions.

        This method is called by ``gdb`` to implement the command.

        It translates the :class:`.CommandError`, :class:`.CommandLineError`,
        and :class:`.DelayedAttributeError` exceptions into readable
        error messages.

        Unless you are doing something special, see :meth:`execute` instead.

        Args:
            argstr: The command arguments
            from_tty (default=False): Whether the command was invoked from a
                tty.
        """
        try:
            self.invoke_uncaught(argstr, from_tty)
        except CommandError as e:
            print(f"{self.name}: {str(e)}")
        except CommandLineError as e:
            print(f"{self.name}: {str(e)}")
            self._parser.print_usage()
        except DelayedAttributeError as e:
            print(f"{self.name}: command unavailable, {str(e)}")
        except (SystemExit, KeyboardInterrupt):
            pass

    def execute(self, args: argparse.Namespace) -> None:
        """
        This method implements the command functionality.

        Each command has a derived class associated with it that,
        minimally, implements this method.

        Args:
            args: The arguments to this command already parsed by the
                commmand's parser.
        """
        raise NotImplementedError("Command should not be called directly")

def discover() -> None:
    modules = glob.glob(os.path.dirname(__file__)+"/[A-Za-z]*.py")
    __all__ = [os.path.basename(f)[:-3] for f in modules]

    mods = __all__
    for mod in mods:
        # pylint: disable=unused-variable
        x = importlib.import_module("crash.commands.{}".format(mod))
