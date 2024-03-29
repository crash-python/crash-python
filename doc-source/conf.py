#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# crash-python documentation build configuration file, created by
# sphinx-quickstart on Tue May 28 12:52:41 2019.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('./mock'))
sys.path.insert(0, os.path.abspath('.'))

from sphinx.ext import autodoc
from sphinx.errors import ExtensionError

def run_apidoc(_):
    try:
        from sphinx.ext.apidoc import main
    except ImportError as e:
        from sphinx.apidoc import main
    import gen_command_docs
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    cur_dir = os.path.abspath(os.path.dirname(__file__))

    out_dir = os.path.join(cur_dir, "crash")
    mod_dir = os.path.join(cur_dir, "..", "crash")
    argv = [ '-M', '-e', '-H', 'Crash API Reference', '-f',
            '-o', out_dir, mod_dir , f'*crash/commands/[a-z]*' ]
    main(argv)

    # We want to document the commands as part of the command reference
    # not the API documentation.
    f = open(f"{cur_dir}/crash/crash.commands.rst")
    lines = f.readlines()
    f.close()
    f = open(f"{cur_dir}/crash/crash.commands.rst", "w")
    printit = True
    for line in lines:
        if 'Submodules' in line:
            printit = False
        elif 'Module contents' in line:
            printit = True

        if printit:
            print(line, file=f, end='')
    f.close()


    print("*** Generating doc templates")

    gen_command_docs.gen_command_docs(cur_dir)

def init_callback(x, y):
    import make_gdb_refs
    import os
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    make_gdb_refs.make_gdb_refs(cur_dir)

def setup(app):
    try:
        app.connect('config-inited', init_callback)
    except ExtensionError as e:
        pass

    app.connect('builder-inited', run_apidoc)


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.coverage',
              'sphinx.ext.intersphinx',
              'sphinx.ext.viewcode',
              'sphinx.ext.napoleon']

intersphinx_mapping = { 'gdb' :
        ("https://sourceware.org/gdb/onlinedocs/gdb/", "gdb.inv") }

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'crash-python'
copyright = '2019, Jeff Mahoney'
author = 'Jeff Mahoney'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
#html_sidebars = {
#    '**': [
#        'relations.html',  # needs 'show_related': True theme option to display
#        'searchbox.html',
#    ]
#}

html_theme_options = {
    'description': 'Kernel debugger in Python',
    'logo_name': True,
    'logo_text_align': 'center',
    'github_user': 'jeffmahoney',
    'github_repo': 'crash-python',
    'github_button': True,
    'github_type': 'star',
}


# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'crash-pythondoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'crash-python.tex', 'crash-python Documentation',
     'Jeff Mahoney', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('crash-python', 'crash-python', 'crash-python Documentation',
     [author], 1),
    ('crash-python', 'pycrash', 'crash-python Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'crash-python', 'crash-python Documentation',
     author, 'crash-python', 'One line description of project.',
     'Miscellaneous'),
]



# Temporary workaround for 5.1.0 bug
import sphinx
if sphinx.__version__ == '5.1.0':
    # see https://github.com/sphinx-doc/sphinx/issues/10701
    # hope is it would get fixed for the next release

    # Although crash happens within NumpyDocstring, it is subclass of GoogleDocstring
    # so we need to overload method there
    from sphinx.ext.napoleon.docstring import GoogleDocstring
    from functools import wraps

    @wraps(GoogleDocstring._consume_inline_attribute)
    def _consume_inline_attribute_safe(self):
        try:
            return self._consume_inline_attribute_safe()
        except:
            return "", []

    GoogleDocstring._consume_inline_attribute = _consume_inline_attribute_safe

