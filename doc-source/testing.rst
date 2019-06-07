Testing
=======

Summary
-------

There are unit tests in the ``tests`` directory that are standalone and
useful for testing basic functionality.

There are unit tests in the ``kernel-tests`` directory that require
configuration, kernel images, debuginfo, and vmcores to use.

If installed, there is support for running the `mypy <http://mypy-lang.org/>`_
static checker and the `pylint <https://www.pylint.org/>`_ code checker.

Unit tests
----------

The standalone unit tests are in the tests directory and are prefixed
with ``test_``.  Only tests that don't need to access a real vmcore should
go here.  This is mostly basic sanity testing.

To run the unit tests:

.. code-block:: bash

    $ make unit-tests

Adding new tests is as easy as creating a new python file using a filename
prefixed with ``test_``.  It uses the
`unittest <https://docs.python.org/3/library/unittest.html>`_ framework and
the tests are run from within the ``gdb`` python environment.

Other test cases can be used as examples.

Type checking
-------------

Although python isn't static typed as in languages like
`C <https://en.wikipedia.org/wiki/C_(programming_language)>`_, Python 3.5
added support for `typing <https://docs.python.org/3/library/typing.html>`_
to be used for static analysis.  The crash-python project uses the typing
facility extensively and requires that new code be properly typed.  The
typing can be verified using the `mypy <http://mypy-lang.org/>`_ tool.

If ``mypy`` is installed, the following will invoke it.

.. code-block:: bash

    $ make static-check

The tool does spawn external interpreters and so it currently does not
operate properly from within the ``gdb`` python environment.  We've worked
around that shortcoming by ignoring missing imports.

Code sanitization
-----------------

One of the tools available to ensure that python code is free of certain
classes of bugs and that it conforms to typical conventions, is the
`pylint <https://www.pylint.org/>` code checker.  The crash-python project
requires that all new code pass the ``pylint`` checks or be properly
annotated as to why a particular addition doesn't pass.

There are some checks that are an expression of the developer's preference
and those have been disabled:

- ``missing-docstring``
- ``too-few-public-methods``
- ``invalid-name``
- ``too-many-locals``
- ``too-many-instance-attributes``
- ``too-many-public-methods``
- ``fixme``
- ``no-self-use``
- ``too-many-branches``
- ``too-many-statements``
- ``too-many-arguments``
- ``too-many-boolean-expressions``
- ``line-too-long``
- ``duplicate-code``

If ``pylint`` is installed, the following will invoke it.

.. code-block:: bash

    $ make lint

The ``lint`` target does allow several options:

- ``E=1`` -- Only report errors
- ``PYLINT_ARGS`` -- Override the default arguments.  It will still operate
  on the :py:mod:`crash` and :py:mod:`kdump` modules but no other default
  arguments will be used.

Testing with vmcores
--------------------

Basic unit tests are helpful for shaking out simple bugs but many failures
can occur in response to the data contained in real crash dumps.  Symbols
may be missing or changed.  Types may have members added or removed.  Flags
may have changed semantic meaning or numeric value.  A semantic debugger
must be continually updated as new kernel versions are released that change
interfaces.

The best way to ensure that the debugger operates on a particular kernel
release is to use the live testing functionality provided by the ``live-tests``
target.  In order to provide a flexible environment for enabling those
tests, the configuration for each kernel to be tested is contained in
an individual `.ini` file.  The ``kernel`` and ``vmcore`` fields are
mandatory.  Any other fields are optional and defaults will be used if they
are unspecified.  The fields and their defaults match those defined in
:py:class:`crash.kernel.CrashKernel`.

.. code-block:: ini

    [test]
    kernel=/path/to/kernel
    vmcore=/path/to/vmcore
    vmlinux_debuginfo=/path/to/vmlinux-debuginfo
    modules=/path/to/modules
    module_debuginfo_path=/path/to/module/debuginfo
    root=/root/for/tree/searches

Like running the debugger normally, modules and debuginfo are required for
testing.   Missing modules will prevent module-specific tests being run
and they will be skipped without failing the test.

Example 1:

.. code-block:: ini

    [test]
    kernel=/var/crash/2019-04-23-11:35/vmlinux-4.12.14-150.14-default.gz
    vmcore=/var/crash/2019-04-23-11:35/vmcore

In this example, the kernel and debuginfo packages are installed in the
default locations and will be searched automatically.

Example 2:

.. code-block:: ini

    [test]
    kernel=/var/crash/2019-04-23-11:35/vmlinux-4.12.14-150.14-default.gz
    vmcore=/var/crash/2019-04-23-11:35/vmcore
    root=/var/cache/crash-setup/leap15/4.12.14-150.14-default

In this example, the kernel and debuginfo packages are installed under
``/var/cache/crash-setup/leap15/4.12.14-150.14-default`` and so we only
specify a root directory.

To invoke these test scenarios, the ``live-tests`` target can be used with
the ``INI_FILES`` option.  The ``INI_FILES`` option is a quoted,
space-separated list of paths to the `.ini` files described above.

Example:

.. code-block:: bash

    $ make live-tests INI_FILES='kernel-test-configs/4.12.14-150.14-default.ini kernel-test-configs/5.1.0-rc7-vanilla.ini'


or

.. code-block:: bash

    $ make live-tests INI_FILES=kernel-test-configs/*.ini

Each configuration will execute independently from one another.

Similar to the standalone unit tests, adding a new test is as simple as
creating a new python file with a name prefixed with ``test_`` and
creating the testcases.

Test everything
---------------

To run all standalone tests:

.. code-block:: bash

    $ make test

To run all tests, including testing real vmcores, specify the ``INI_FILES``
option as described above.

.. code-block:: bash

    $ make test INI_FILES=kernel-test-configs/*.ini

The absence of ``pylint`` or ``mypy`` is not considered an error.

Lastly, documentation is built using docstrings found in the code.  Building
documentation requires the
`sphinx-apidoc <https://www.sphinx-doc.org/en/master/man/sphinx-apidoc.html>`_
package and the `sphinx <https://www.sphinx-doc.org/en/master/index.html>`_
package with the
`autodoc <https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html>`_,
`coverage <https://www.sphinx-doc.org/en/master/usage/extensions/coverage.html>`_,
`intersphinx <https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html>`_,
`viewcode <https://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html>_`, and
`napoleon <https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html>`_ extensions.

To test everything including documentation:

.. code-block:: bash

    $ make full-test <options>


The documentation is published on `readthedocs.org <https://readthedocs.org>`_
which doesn't provide a ``gdb`` environment or the required dependencies
(nor should it).  In order to build the documentation properly, mock
interfaces to those packages are used.  If you've added code that requires
extending the mock interfaces, they can be found in the ``doc-source/mock``
directory of the source code
`repository <https://github.com/jeffmahoney/crash-python>`_.
