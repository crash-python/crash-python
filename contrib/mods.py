#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

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
#path = "./modules/{}".format(sys.cache.utsname_cache['release'])
path = "./modules/"
path_debug = "./modules.debug/"

modules = gdb.lookup_symbol('modules', None)[0].value()
module_type = gdb.lookup_type('struct module')
for module in list_for_each_entry(modules, module_type, 'list'):
    modname = "{}.ko".format(module['name'].string())
    modpath = find(modname, path)
    if not modpath and modname.find('_') != -1:
        modname = modname.replace('_', '-')
        modpath = find(modname, path)
    if not modpath:
        print("Couldn't find {} under {}.".format(module['name'], path));
        continue
    gdb.execute("add-symbol-file {} {}".format(modpath, module['module_core']))

for mod in gdb.objfiles():
    modfile = mod.filename
    if modfile == "vmlinux":
        continue
    # we could also just s/modules/modules.debug/
    modname = modfile.split('/')[-1] + ".debug"
    modpath = find(modname, path_debug)
    if not modpath and modname.find('_') != -1:
        modname = modname.replace('_', '-')
        modpath = find(modname, path_debug)
    if not modpath:
        print "Couldn't find {} under {}.".format(modname, path_debug)
        continue
    mod.add_separate_debug_file(modpath)

    
