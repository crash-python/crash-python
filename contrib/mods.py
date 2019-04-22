#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from crash.types.list import list_for_each_entry
import gdb
import uuid
from crash.cache import sys
import os

def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)

sys.cache.init_sys_caches()
path = "/lib/modules/{}".format(sys.cache.utsname_cache['release'])

modules = gdb.lookup_symbol('modules', None)[0].value()
module_type = gdb.lookup_type('struct module')
for module in list_for_each_entry(modules, module_type, 'list'):
    modname = "{}.ko".format(module['name'].string())
    modpath = find(modname, path)
    if not modpath and modname.find('_') != -1:
        modname = modname.replace('_', '-')
        modpath = find(modname, path)
    if not modpath:
        print "Couldn't find {} under {}.".format(module['name'], path)
        continue
    gdb.execute("add-symbol-file {} {}".format(modpath, module['module_core']))
