API Changes
===========

April 2019
----------

In April-June 2019, significant development effort was invested in improving code quality.  The following changes were the result of that work.

Python 3.6 Required
-------------------

A system using Python 3.6 or newer is required.  Recent development has taken advantage of features introduced in Python versions as recent as 3.6:

- `typing for function parameters and return values <https://docs.python.org/3/library/typing.html>`_ Introduced in 3.5
- `typing for variables <https://docs.python.org/3/whatsnew/3.6.html#whatsnew36-pep526>`_ -- Introduced in 3.6
- `f-strings <https://docs.python.org/3/reference/lexical_analysis.html#f-strings>`_ -- Introduced in 3.6

This also means:

- Python 2/3 compatibility hacks are obsolete and removed:

  - ``long = int if sys.version.major > 3``
  - ``from __future__`` imports

- Exception handling uses ``except <exception> as <name>`` syntax

- Absolute imports are required

- f-strings are preferred -- though there are cases where ``str.format()`` is still useful (e.g. with a static format string and per-call formatting).

  - There is much outstanding work in converting existing strings to f-strings, but it has not been a development priority.

Typing
------

As part of the drive to improve code quality, I've added typing to every function and method in the project. ``make test`` with `mypy <http://mypy-lang.org/>`_ installed will fail if there are functions or methods (or dependent variables) without typing information.  In the example below, the new version of ``MyClass`` has several examples of typing in use.

Public / Protected Namespace
----------------------------

The use of ``_`` as a prefix for protected members of classes is now expected and will be enforced during ``make test`` if `pylint <https://www.pylint.org/>`_ is installed.  In the example below, several internal members and methods of `MyClass` have been renamed to indicate that they are
protected.

New mechanism for delayed lookups
---------------------------------

In earlier versions of crash-python, the way to pull symbols and types in your classes was to inherit from :class:`crash.infra.CrashBaseClass` and to export symbols desired in the global namespace by using the :func:`crash.infra.export` decorator.  The infrastructure to make this work was complex and esoteric and formed a barrier to entry with benefits that were dwarfed by the cost of knowledge ramp-up to maintain it. It also required the developer to declare a class to contain the declarations even if a class wasn't really required for the implementation.

The current version of crash-python uses the :class:`crash.util.symbol` module to do delayed lookups.  This has several advantages:

- These can be declared in class or module context (or object context, but there's no real reason to do it, IMO).

- The namespaces are separated.  There are no collisions within the host class as inferred names override class-defined names.

- There are accessors beyond attributes.  The :class:`.DelayedCollection` family of classes all have :meth:`~.DelayedCollection.__getattr__`, :meth:`~DelayedCollection.__getitem__`, and :meth:`~DelayedCollection.get` defined, so they can be accessed as attribute names, dictionary keys, or by function call.  The latter two can be used with any name, but the attribute names cannot be used for symbols that start with ``__``.

Example
-------

An older crash-python module might look like:

.. code-block:: py

    from crash.infra import CrashBaseClass, export

    class MyClass(CrashBaseClass):
        __types__ = ['struct task_struct']
        __symvals__ = ['init_task']
        __symbol_callbacks__ = [('init_task', 'setup_init_task')]
        valid = False

        def __init__(self, task):
            self.init_task_types(task)

        @classmethod
        def setup_init_task(cls, task):
            # do something
            pass

        @classmethod
        def init_task_types(cls, task):
            if not cls.valid:
                if task.type == self.task_struct_type:
                    self.task_struct_type = task.type

                cls.valid = True

        def some_method(self):
            print("i have an init_task at {:x}".format(int(self.init_task.address)))

        @export
        def for_each_task(self):
            task_list = self.init_task['tasks']
            for task in list_for_each_entry(task_list, self.task_struct_type,
                                            'task', include_head=True):
                thread_list = task['thread_group']
                for thread in list_for_each_entry(thread_list,
                                                  self.task_struct_type,
                                                  'thread_group'):
                    yield thread



With :class:`CrashBaseClass` removed, typing added, f-string formatting used, and the code restructured to only put the minimum (contrived here) functionality in ``MyClass``, that same code looks like:

.. code-block:: py

    from typing import Iterable
    from crash.util.symbols import Types, Symvals, SymbolCallbacks

    types = Types(['struct task_struct'])
    symvals = Symvals(['init_task'])

    class MyClass:
        _valid = False

        def __init__(self, task: gdb.Value) -> None:
                self._init_task_types(task)

        @classmethod
        def _init_task_types(cls, task: gdb.Value) -> None:
            if not cls._valid:
                if task.type == self.task_struct_type:
                    types.override('struct task_struct',  task.type)

                cls._valid = True

        @classmethod
        def _setup_init_task(cls) -> None:
            # do something
            pass

    symbol_cbs = SymbolCallbacks([('init_task', MyClass._setup_init_task)])

    def some_method() -> None:
        print(f"i have an init_task at {int(symvals.init_task.address):#x}")

    def for_each_task() -> Iterable[gdb.Value]:
        task_list = symvals.init_task['tasks']
        for task in list_for_each_entry(task_list, types.task_struct_type,
                                        'task', include_head=True):
            thread_list = task['thread_group']
            for thread in list_for_each_entry(thread_list,
                                              types.task_struct_type,
                                              'thread_group'):
                yield thread
