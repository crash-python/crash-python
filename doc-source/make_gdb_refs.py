#!/usr/bin/python3

# This creates a mock objects.inv file to reference external documentation

from sphinx.ext import intersphinx
from sphinx.util.inventory import InventoryFile

class config(object):
    def __init__(self, project, version):
        self.project = project
        self.version = version

# type: () -> Iterator[Tuple[unicode, unicode, unicode, unicode, unicode, int]]

# modules:
# modname, modname, 'module', "info[0]", 'module-' + modname, 0
# objects:
# refname, refname, type, docname, refname, 1
class MockDomain(object):
    def __init__(self, name):
        self.name = name
        self.objects = dict()

    def add_class_ref(self, name, doc):
        self.objects[name] = doc

    def get_objects(self):
        for name, doc in self.objects.items():
            yield (name, name, 'class', doc, name, 1)

class MockEnvironment(object):
    def __init__(self):
        self.domains = dict()
        self.config = config('gdb', '8.3')

    def add_domain(self, domain):
        self.domains[domain.name] = domain

class MockBuilder(object):

    def get_target_uri(self, docname):
        return docname

def make_gdb_refs():
    env = MockEnvironment()
    builder = MockBuilder()

    classes = MockDomain('py')

    classes.add_class_ref('gdb.Type', 'Types-In-Python.html')
    classes.add_class_ref('gdb.Symbol', 'Symbols-In-Python.html')
    classes.add_class_ref('gdb.Command', 'Commands-In-Python.html')
    classes.add_class_ref('gdb.Inferior', 'Inferiors-In-Python.html')
    classes.add_class_ref('gdb.Objfile', 'Objfiles-In-Python.html')
    classes.add_class_ref('gdb.Value', 'Values-From-Inferior.html')
    classes.add_class_ref('gdb.InferiorThread', 'Threads-In-Python.html')
    classes.add_class_ref('gdb.Frame', 'Frames-In-Python.html')
    classes.add_class_ref('gdb.NotAvailableErorr', 'Exception-Handling.html')
    classes.add_class_ref('gdb.MemoryError', 'Exception-Handling.html')
    classes.add_class_ref('gdb.error', 'Exception-Handling.html')
    classes.add_class_ref('gdb.GdbError', 'Exception-Handling.html')

    env.add_domain(classes)

    InventoryFile.dump("gdb.inv", env, builder)
