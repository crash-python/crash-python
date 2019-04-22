# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import sys
import os.path
import crash.arch
import crash.arch.x86_64
import crash.arch.ppc64
from crash.infra import CrashBaseClass, export
from crash.types.list import list_for_each_entry
from crash.types.percpu import get_percpu_vars
from crash.types.list import list_for_each_entry
from crash.types.module import for_each_module, for_each_module_section
import crash.cache.tasks
from crash.types.task import LinuxTask
from elftools.elf.elffile import ELFFile
from crash.util import get_symbol_value

LINUX_KERNEL_PID = 1

class CrashKernel(CrashBaseClass):
    __symvals__ = [ 'init_task' ]
    __symbols__ = [ 'runqueues']

    def __init__(self, searchpath=None):
        self.findmap = {}
        self.searchpath = searchpath

        sym = gdb.lookup_symbol('vsnprintf', None)[0]
        if sym is None:
            raise RuntimeError("Missing vsnprintf indicates that there is no kernel image loaded.")

        f = open(gdb.objfiles()[0].filename, 'rb')
        self.elffile = ELFFile(f)

        archname = sym.symtab.objfile.architecture.name()
        archclass = crash.arch.get_architecture(archname)
        self.arch = archclass()

        self.target = gdb.current_target()
        self.vmcore = self.target.kdump

        self.target.fetch_registers = self.fetch_registers
        self.crashing_thread = None

    def fetch_registers(self, register):
        thread = gdb.selected_thread()
        return self.arch.fetch_register(thread, register.regnum)

    def get_module_sections(self, module):
        out = []
        for (name, addr) in for_each_module_section(module):
            out.append("-s {} {:#x}".format(name, addr))
        return " ".join(out)

    def load_modules(self, verbose=False):
        print("Loading modules...", end='')
        sys.stdout.flush()
        failed = 0
        loaded = 0
        for module in for_each_module():
            modname = "{}".format(module['name'].string())
            modfname = "{}.ko".format(modname)
            found = False
            for path in self.searchpath:
                modpath = self.find_module_file(modfname, path)
                if not modpath:
                    continue

                found = True

                if 'module_core' in module.type:
                    addr = int(module['module_core'])
                else:
                    addr = int(module['core_layout']['base'])

                if verbose:
                    print("Loading {} at {:#x}".format(modname, addr))
                sections = self.get_module_sections(module)
                gdb.execute("add-symbol-file {} {:#x} {}"
                            .format(modpath, addr, sections),
                            to_string=True)
                sal = gdb.find_pc_line(addr)
                if sal.symtab is None:
                    objfile = gdb.lookup_objfile(modpath)
                    self.load_debuginfo(objfile, modpath)

                # We really should check the version, but GDB doesn't export
                # a way to lookup sections.
                break

            if not found:
                if failed == 0:
                    print()
                print("Couldn't find module file for {}".format(modname))
                failed += 1
            else:
                loaded += 1
            if (loaded + failed) % 10 == 10:
                print(".", end='')
                sys.stdout.flush()
        print(" done. ({} loaded".format(loaded), end='')
        if failed:
            print(", {} failed)".format(failed))
        else:
            print(")")

        # We shouldn't need this again, so why keep it around?
        del self.findmap
        self.findmap = {}

    def find_module_file(self, name, path):
        if not path in self.findmap:
            self.findmap[path] = {}

            for root, dirs, files in os.walk(path):
                for filename in files:
                    nname = filename.replace('-', '_')
                    self.findmap[path][nname] = os.path.join(root, filename)
        try:
            nname = name.replace('-', '_')
            return self.findmap[path][nname]
        except KeyError:
            return None

    def load_debuginfo(self, objfile, name=None, verbose=False):
        if name is None:
            name = objfile.filename
        if ".gz" in name:
            name = name.replace(".gz", "")
        filename = "{}.debug".format(os.path.basename(name))
        filepath = None

        # Check current directory first
        if os.path.exists(filename):
            filepath = filename
        else:
            for path in self.searchpath:
                filepath = self.find_module_file(filename, path)
                if filepath:
                    break

        if filepath:
            objfile.add_separate_debug_file(filepath)
        else:
            print("Could not locate debuginfo for {}".format(name))

    def setup_tasks(self):
        gdb.execute('set print thread-events 0')

        task_list = self.init_task['tasks']

        rqs = get_percpu_vars(self.runqueues)
        rqscurrs = {int(x["curr"]) : k for (k, x) in rqs.items()}

        self.pid_to_task_struct = {}

        print("Loading tasks...", end='')
        sys.stdout.flush()

        task_count = 0
        tasks = []
        for taskg in list_for_each_entry(task_list, self.init_task.type,
                                         'tasks', include_head=True):
            tasks.append(taskg)
            for task in list_for_each_entry(taskg['thread_group'],
                                            self.init_task.type,
                                            'thread_group'):
                tasks.append(task)

        try:
            crashing_cpu = int(get_symbol_value('crashing_cpu'))
        except Exception as e:
            crashing_cpu = None

        for task in tasks:
            cpu = None
            regs = None
            active = int(task.address) in rqscurrs
            if active:
                cpu = rqscurrs[int(task.address)]
                regs = self.vmcore.attr.cpu[cpu].reg

            ltask = LinuxTask(task, active, cpu, regs)
            ptid = (LINUX_KERNEL_PID, task['pid'], 0)

            try:
                thread = gdb.selected_inferior().new_thread(ptid, ltask)
            except gdb.error as e:
                print("Failed to setup task @{:#x}".format(int(task.address)))
                continue
            thread.name = task['comm'].string()
            if active and crashing_cpu is not None and cpu == crashing_cpu:
                self.crashing_thread = thread

            self.arch.setup_thread_info(thread)
            ltask.attach_thread(thread)
            ltask.set_get_stack_pointer(self.arch.get_stack_pointer)

            crash.cache.tasks.cache_task(ltask)

            task_count += 1
            if task_count % 100 == 0:
                print(".", end='')
                sys.stdout.flush()
        print(" done. ({} tasks total)".format(task_count))

        gdb.selected_inferior().executing = False
