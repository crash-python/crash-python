# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
import sys
import os.path
from crash.infra import CrashBaseClass, export
from crash.types.list import list_for_each_entry
from crash.types.percpu import get_percpu_var
from crash.types.list import list_for_each_entry
import crash.cache.tasks
from crash.types.task import LinuxTask
import crash.kdump
import crash.kdump.target
from kdumpfile import kdumpfile
from elftools.elf.elffile import ELFFile

LINUX_KERNEL_PID = 1

class CrashKernel(CrashBaseClass):
    __types__ = [ 'struct module' ]
    __symvals__ = [ 'modules', 'init_task' ]
    __symbols__ = [ 'runqueues']

    def __init__(self, vmlinux_filename, searchpath=None):
        self.findmap = {}
        self.vmlinux_filename = vmlinux_filename
        self.searchpath = searchpath

        f = open(self.vmlinux_filename, 'rb')
        self.elffile = ELFFile(f)

        self.set_gdb_arch()

    def set_gdb_arch(self):
        mach = self.elffile['e_machine']
        e_class = self.elffile['e_ident']['EI_CLASS']

        elf_to_gdb = {
            ('EM_X86_64', 'ELFCLASS64') : 'i386:x86-64',
            ('EM_386', 'ELFCLASS32')    : 'i386',
            ('EM_S390', 'ELFCLASS64')   :  's390:64-bit',
            ('EM_PPC64', 'ELFCLASS64')   :  'powerpc:common64'
        }

        try:
            gdbarch = elf_to_gdb[(mach, e_class)]
        except KeyError as e:
            raise RuntimeError("no mapping for {}:{} to gdb architecture found.".format(mach, e_class))
        gdb.execute("set arch {}".format(gdbarch), to_string=True)

    def open_kernel(self):
        if self.base_offset is None:
            raise RuntimeError("Base offset is unconfigured.")

        self.load_sections()

        try:
            list_type = gdb.lookup_type('struct list_head')
        except gdb.error as e:
            self.load_debuginfo(gdb.objfiles()[0], None)
            try:
                list_type = gdb.lookup_type('struct list_head')
            except gdb.error as e:
                raise RuntimeError("Couldn't locate debuginfo for {}"
                                   .format(self.vmlinux_filename))

        self.target.setup_arch()

    def get_sections(self):
        sections = {}

        text = self.elffile.get_section_by_name('.text')

        for section in self.elffile.iter_sections():
            if (section['sh_addr'] < text['sh_addr'] and
                section.name != '.data..percpu'):
                continue
            sections[section.name] = section['sh_addr']

        return sections

    def load_sections(self):
        sections = self.get_sections()

        line = ""

        # .data..percpu shouldn't have relocation applied but it does.
        # Perhaps it's due to the address being 0 and it being handled
        # as unspecified in the parameter list.
#        for section, addr in sections.items():
#            if addr == 0:
#                line += " -s {} {:#x}".format(section, addr)

        # The gdb internals are subtle WRT how symbols are mapped.
        # Minimal symbols are mapped using the offset for the section
        # that contains them.  That means that using providing an address
        # for .text here gives a base address with no offset and minimal
        # symbols in .text (like __switch_to_asm) will not have the correct
        # addresses after relocation.
        cmd = "add-symbol-file {} -o {:#x} {} ".format(self.vmlinux_filename,
                                                       self.base_offset, line)
        gdb.execute(cmd, to_string=True)

    def attach_vmcore(self, vmcore_filename, debug=False):
        self.vmcore_filename = vmcore_filename
        self.vmcore = kdumpfile(vmcore_filename)
        self.target = crash.kdump.target.Target(self.vmcore, debug)

        self.base_offset = 0
        try:
            KERNELOFFSET = "linux.vmcoreinfo.lines.KERNELOFFSET"
            attr = self.vmcore.attr.get(KERNELOFFSET, "0")
            self.base_offset = int(attr, base=16)
        except Exception as e:
            print(e)

    def for_each_module(self):
        for module in list_for_each_entry(self.modules, self.module_type,
                                          'list'):
            yield module

    def get_module_sections(self, module):
        attrs = module['sect_attrs']
        out = []
        for sec in range(0, attrs['nsections']):
            attr = attrs['attrs'][sec]
            name = attr['name'].string()
            if name == '.text':
                continue
            out.append("-s {} {:#x}".format(name, int(attr['address'])))

        return " ".join(out)

    def load_modules(self, verbose=False):
        print("Loading modules...", end='')
        sys.stdout.flush()
        failed = 0
        loaded = 0
        for module in self.for_each_module():
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

        rqs = get_percpu_var(self.runqueues)
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

            self.target.arch.setup_thread_info(thread)
            ltask.attach_thread(thread)
            ltask.set_get_stack_pointer(self.target.arch.get_stack_pointer)

            crash.cache.tasks.cache_task(ltask)

            task_count += 1
            if task_count % 100 == 0:
                print(".", end='')
                sys.stdout.flush()
        print(" done. ({} tasks total)".format(task_count))

        gdb.selected_inferior().executing = False
