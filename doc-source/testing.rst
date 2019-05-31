Testing
=======

Summary
-------

There are unit tests in the tests/ dir that are standalone and useful for
testing basic functionality.

There are unit tests in the kernel-tests dir that require configuration,
kernel images, debuginfo, and vmcores to use.

If installed, there is support for running the `mypy <http://mypy-lang.org/>`_
static checker and the `pylint <https://www.pylint.org/>`_ code checker.

`pylint` runs properly from within the gdb environment but `mypy` spawns
external interpreters and cannot run from within gdb.

Configuration
-------------

The configuration for each kernel/vmcore to be tested goes in a .ini file
with the following format.  All fields except kernel and vmcore are
optional, and defaults will be used.  A kernel missing debuginfo cannot
be used for testing.  Missing modules will mean module-specific tests
will be skipped.

.. code-block:: ini

    [test]
    kernel=/path/to/kernel
    vmcore=/path/to/vmcore
    vmlinux_debuginfo=/path/to/vmlinux-debuginfo
    modules=/path/to/modules
    module_debuginfo_path=/path/to/module/debuginfo
    root=/root/for/tree/searches

The optional fields match those defined in `crash.kernel.CrashKernel`.

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
/var/cache/crash-setup/leap15/4.12.14-150.14-default and so we only
specify a root directory.

Running
-------

The make target `test` will run all standalone tests.  The absence of `pylint`
or `mypy` is not considered an error.

To run the tests using live vmcores using the configuration detailed above,
the `INI_FILES` option should be used.

Example:

.. code-block:: bash

    $ make live-tests INI_FILES='kernel-test-configs/4.12.14-150.14-default.ini kernel-test-configs/5.1.0-rc7-vanilla.ini'


or

.. code-block:: bash

    $ make live-tests INI_FILES=kernel-test-configs/*.ini


Each configuration will execute independently from one another.

