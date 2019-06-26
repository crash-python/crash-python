Development
===========

.. toctree::
   :maxdepth: 2

   api_changes
   testing
   kdump/modules
   crash/modules

   gdb-internals
   patterns


Documentation is automatically built from the python code for the user
guide, command help text, and API reference.

There are several make targets to assist in your development efforts:

- ``make`` or ``make all``  -- Start fresh, build the python code
  and documentation, and then run the standalone test suite.

- ``make doc`` -- Build all documentation (html, text, and man page).

- ``make doc-help`` -- Build only the documentation required for help text

- ``make doc-html`` -- Build the user manual

- ``make man`` -- Build the man page

For testing, see the :doc:`testing` section.

To develop a command, see the :mod:`crash.commands` API.

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
