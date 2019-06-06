# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

import sys
import io
import re
import fnmatch

from crash.commands import CommandError, CommandLineError
from crash.commands.ps import PSCommand
import crash.types.task as tasks

from decorators import bad_command_line, unimplemented

PF_KTHREAD = 0x200000

class TestCommandsPs(unittest.TestCase):
    def setUp(self):
        self.stdout = sys.stdout
        self.redirected = io.StringIO()
        sys.stdout = self.redirected
        self.command = PSCommand()
        self.do_output = False

    def tearDown(self):
        sys.stdout = self.stdout
        if self.do_output:
            print(self._output())

    def _output(self):
        return self.redirected.getvalue()

    def output(self):
        try:
            return self.output_list
        except AttributeError:
            self.output_list = self._output().split("\n")
            return self.output_list

    def output_lines(self):
        output = self.output()
        return len(output) - 1

    def get_wildcard_regex(self, wildcard):
        return re.compile(fnmatch.translate(wildcard))

    def check_line_count(self, count):
        self.assertTrue(self.output_lines() == count)

    def check_header(self, expected):
        header = self.output()[0]
        self.assertTrue(re.match(expected, header) is not None)

    def check_task_header(self):
        regex = "\s+PID\s+PPID\s+CPU\s+TASK\s+ST\s+%MEM\s+VSZ\s+RSS\s+COMM"
        self.check_header(regex)

    def check_kstack_header(self):
        regex = "\s+PID\s+PPID\s+CPU\s+KSTACK\s+ST\s+%MEM\s+VSZ\s+RSS\s+COMM"
        self.check_header(regex)

    def check_threadnum_header(self):
        regex = "\s+PID\s+PPID\s+CPU\s+THREAD#\s+ST\s+%MEM\s+VSZ\s+RSS\s+COMM"
        self.check_header(regex)

    def check_body(self, regex, start=1):
        comp = re.compile(regex)
        lines = 0
        for line in self.output()[start:-1]:
            self.assertTrue(comp.match(line) is not None)
            lines += 1

        self.assertTrue(lines > 0)

    def check_threadnum_output(self):
        regex = ">?\s+\d+\s+\d+\s+\d+\s+\d+\s+[A-Z]+\s+[\d\.]+\s+\d+\s+\d+\s+.*"

        self.check_body(regex)


    def check_normal_output(self):
        regex = ">?\s+\d+\s+\d+\s+\d+\s+[\d+a-f]+\s+[A-Z]+\s+[\d\.]+\s+\d+\s+\d+\s+.*"

        self.check_body(regex)

    def check_last_run_output(self):
        regex = "\[\d+\]\s+\[[A-Z][A-Z]\]\s+PID:\s+\d+\s+TASK:\s+[\da-f]+\s+CPU:\s+\d+\s+COMMAND: \".*\""
        self.check_body(regex, 0)

    def check_no_matches_output(self):
        self.check_header('No matches for.*')
        lines = self.output_lines()
        self.assertTrue(lines == 1)

    def is_kernel_thread(self, task):
        return (int(task['flags']) & PF_KTHREAD)

    def is_user_task(self, task):
        return not self.is_kernel_thread(task)

    def task_name(self, task_struct):
        return task_struct['comm'].string()

    def count_tasks(self, test=None, regex=None):
        count = 0
        for task in tasks.for_each_all_tasks():
            if test is not None and not test(task):
                continue
            if regex is None or regex.match(self.task_name(task)):
                count += 1

        return count

    def count_kernel_tasks(self, regex=None):
        return self.count_tasks(self.is_kernel_thread, regex)

    def count_user_tasks(self, regex=None):
        return self.count_tasks(self.is_user_task, regex)

    def count_thread_group_leaders(self, regex=None):
        count = 0
        for task in tasks.for_each_thread_group_leader():
            if regex is None or regex.match(self.task_name(task)):
                count += 1

        return count

    def test_ps_empty(self):
        self.command.invoke_uncaught("")
        self.assertTrue(self.output_lines() > 1)

    def test_ps_wildcard(self):
        self.command.invoke_uncaught("*worker*")

        regex = self.get_wildcard_regex("*worker*")
        self.check_line_count(self.count_tasks(regex=regex) + 1)

    def test_ps_bad_wildcard(self):
        """Test `ps *BaDWiLdCaRd2019*' returns no matches output"""
        self.command.invoke_uncaught("*BaDWiLdCaRd2019*")
        self.check_no_matches_output()

    def test_ps_k(self):
        """Test `ps -k' outputs all (and only) kernel threads"""
        self.command.invoke_uncaught("-k")
        lines = self.output_lines()

        self.check_task_header()
        self.check_normal_output()

        self.check_line_count(self.count_kernel_tasks() + 1)

    def test_ps_k_wildcard(self):
        """Test `ps -k *wonder*' outputs only matching kernel threads"""
        self.command.invoke_uncaught("-k *worker*")
        lines = self.output_lines()

        regex = self.get_wildcard_regex("*worker*")

        self.check_task_header()
        self.check_normal_output()
        self.check_line_count(self.count_kernel_tasks(regex) + 1)

    def test_ps_k_bad_wildcard(self):
        """Test `ps -k *BaDWiLdCaRd2019*' returns no matches output"""
        self.command.invoke_uncaught("-k *BaDWiLdCaRd2019*")
        self.check_no_matches_output()

    def test_ps_u(self):
        """Test `ps -u' outputs all (and only) user tasks"""
        self.command.invoke_uncaught("-u")

        self.check_task_header()
        self.check_normal_output()

        self.check_line_count(self.count_user_tasks() + 1)

    def test_ps_u_wildcard(self):
        """Test `ps -u *wonder*' outputs only matching user tasks"""
        self.command.invoke_uncaught("-u *nscd*")
        lines = self.output_lines()

        regex = self.get_wildcard_regex("*nscd*")

        self.check_task_header()
        self.check_normal_output()

        self.check_line_count(self.count_user_tasks(regex) + 1)

    def test_ps_u_bad_wildcard(self):
        """Test `ps -u *BaDWiLdCaRd2019*' returns no matches output"""
        self.command.invoke_uncaught("-u *BaDWiLdCaRd2019*")
        self.check_no_matches_output()

    def test_ps_g(self):
        """Test `ps -G' outputs all (and only) thread group leaders"""
        self.command.invoke_uncaught("-G")

        self.check_task_header()
        self.check_normal_output()

        self.check_line_count(self.count_thread_group_leaders() + 1)

    def test_ps_g_wildcard(self):
        """Test `ps -G *nscd*' outputs only matching thread group leaders"""
        self.command.invoke_uncaught("-G *nscd*")

        regex = self.get_wildcard_regex("*nscd*")

        self.check_task_header()
        self.check_normal_output()

        self.check_line_count(self.count_thread_group_leaders() + 1)

    def test_ps_g_bad_wildcard(self):
        """Test `ps -G *BaDWiLdCaRd2019*' returns no matches output"""
        self.command.invoke_uncaught("-G *BaDWiLdCaRd2019*")
        self.check_no_matches_output()

    @bad_command_line
    def test_ps_uk(self):
        """Test `ps -u -k'"""
        self.command.invoke_uncaught("-u -k")

    @bad_command_line
    def test_ps_uk_wildcard(self):
        """Test `ps -u -k *'"""
        self.command.invoke_uncaught("-u -k *")

    @bad_command_line
    def test_ps_uG(self):
        """Test `ps -u -G'"""
        self.command.invoke_uncaught("-u -k")

    @bad_command_line
    def test_ps_uG_wildcard(self):
        """Test `ps -u -G *'"""
        self.command.invoke_uncaught("-u -k *")

    @bad_command_line
    def test_ps_kG(self):
        """Test `ps -k -G'"""
        self.command.invoke_uncaught("-k -G")

    @bad_command_line
    def test_ps_kG_wildcard(self):
        """Test `ps -k -G *'"""
        self.command.invoke_uncaught("-k -G *")

    @bad_command_line
    def test_ps_ukG(self):
        """Test `ps -u -k -G'"""
        self.command.invoke_uncaught("-u -k -G")

    @bad_command_line
    def test_ps_ukG_wildcard(self):
        """Test `ps -u -k -G *'"""
        self.command.invoke_uncaught("-u -k -G *")

    def test_ps_s(self):
        """Test `ps -s'"""
        self.command.invoke_uncaught("-s")

        self.check_kstack_header()
        self.check_normal_output()

        self.check_line_count(self.count_tasks() + 1)

    def test_ps_s_wildcard(self):
        """Test `ps -s *nscd*'"""
        self.command.invoke_uncaught("-s *nscd*")

        self.check_kstack_header()
        self.check_normal_output()

        regex = self.get_wildcard_regex("*nscd*")
        self.check_line_count(self.count_tasks(regex=regex) + 1)

    def test_ps_s_bad_wildcard(self):
        """Test `ps -s *BaDWiLdCaRd2019*'"""
        self.command.invoke_uncaught("-s *BaDWiLdCaRd2019*")

        self.check_no_matches_output()

    def test_ps_n(self):
        """Test `ps -n'"""
        self.command.invoke_uncaught("-n")

        self.check_threadnum_header()
        self.check_threadnum_output()

        self.check_line_count(self.count_tasks() + 1)

    def test_ps_n_wildcard(self):
        """Test `ps -n *nscd*'"""
        self.command.invoke_uncaught("-n *nscd*")

        self.check_threadnum_header()
        self.check_threadnum_output()

        regex = self.get_wildcard_regex("*nscd*")
        self.check_line_count(self.count_tasks(regex=regex) + 1)

    def test_ps_n_bad_wildcard(self):
        """Test `ps -n *BaDWiLdCaRd2019*' returns no matches output"""
        self.command.invoke_uncaught("-n *BaDWiLdCaRd2019*")

        self.check_no_matches_output()

    def test_ps_nu(self):
        """Test `ps -n -u'"""
        self.command.invoke_uncaught("-n -u")

        self.check_threadnum_header()
        self.check_threadnum_output()

        self.check_line_count(self.count_user_tasks() + 1)

    def test_ps_nu_wildcard(self):
        """Test `ps -n -u *nscd*'"""
        self.command.invoke_uncaught("-n -u *nscd*")

        self.check_threadnum_header()
        self.check_threadnum_output()

        regex = self.get_wildcard_regex("*nscd*")
        self.check_line_count(self.count_user_tasks(regex) + 1)

    def test_ps_nu_bad_wildcard(self):
        """Test `ps -n -u *BaDWiLdCaRd2019*' returns no matches output"""
        self.command.invoke_uncaught("-n -u *BaDWiLdCaRd2019*")

        self.check_no_matches_output()

    def test_ps_nk(self):
        """Test `ps -n -k'"""
        self.command.invoke_uncaught("-n -k")

        self.check_threadnum_header()
        self.check_threadnum_output()

        self.check_line_count(self.count_kernel_tasks() + 1)

    def test_ps_nk_wildcard(self):
        """Test `ps -n -k *worker*'"""
        self.command.invoke_uncaught("-n -k *worker*")

        self.check_threadnum_header()
        self.check_threadnum_output()

        regex = self.get_wildcard_regex("*worker*")
        self.check_line_count(self.count_kernel_tasks(regex) + 1)

    def test_ps_nk_bad_wildcard(self):
        """Test `ps -n -k *BaDWiLdCaRd2019*' returns no matches output"""
        self.command.invoke_uncaught("-n -k *BaDWiLdCaRd2019*")

        self.check_no_matches_output()

    def test_ps_nG(self):
        """Test `ps -n -G'"""
        self.command.invoke_uncaught("-n -G")

        self.check_threadnum_header()
        self.check_threadnum_output()

        self.check_line_count(self.count_thread_group_leaders() + 1)

    def test_ps_nG_wildcard(self):
        """Test `ps -n -G *nscd*'"""
        self.command.invoke_uncaught("-n -G *nscd*")

        self.check_threadnum_header()
        self.check_threadnum_output()

        regex = self.get_wildcard_regex("*nscd*")
        self.check_line_count(self.count_thread_group_leaders(regex) + 1)

    def test_ps_nG_bad_wildcard(self):
        """Test `ps -n -G *BaDWiLdCaRd2019*' returns no matches output"""
        self.command.invoke_uncaught("-n -G *BaDWiLdCaRd2019*")

        self.check_no_matches_output()

    @unimplemented
    def test_ps_t(self):
        """Test `ps -t'"""
        self.command.invoke_uncaught("-t")

        # Check format

        self.check_line_count(self.count_tasks())

    @unimplemented
    def test_ps_t_wildcard(self):
        """Test `ps -t *nscd*'"""
        self.command.invoke_uncaught("-t *nscd*")

        # Check format

        regex = self.get_wildcard_regex("*nscd*")
        self.check_line_count(self.count_tasks(regex=regex))

    def test_ps_l(self):
        """Test `ps -l'"""
        self.command.invoke_uncaught("-l")

        # No header to test
        self.check_last_run_output()
        self.check_line_count(self.count_tasks())

    def test_ps_l_wildcard(self):
        """Test `ps -l *nscd*'"""
        self.command.invoke_uncaught("-l *nscd*")

        # No header to test
        self.check_last_run_output()

        regex = self.get_wildcard_regex("*nscd*")
        self.check_line_count(self.count_tasks(regex=regex))

    @unimplemented
    def test_ps_p(self):
        """Test `ps -p'"""
        self.command.invoke_uncaught("-p")
        lines = self.output_lines()

        self.assertTrue(lines > 1)

    @unimplemented
    def test_ps_p_wildcard(self):
        """Test `ps -p *nscd*'"""
        self.command.invoke_uncaught("-p *nscd*")
        lines = self.output_lines()

        regex = self.get_wildcard_regex("*nscd*")

        self.assertTrue(lines > 1)

    @unimplemented
    def test_ps_c(self):
        """Test `ps -c'"""
        self.command.invoke_uncaught("-c")
        lines = self.output_lines()

        self.assertTrue(lines > 1)

    @unimplemented
    def test_ps_c_wildcard(self):
        """Test `ps -c *nscd*'"""
        self.command.invoke_uncaught("-c *nscd*")
        lines = self.output_lines()

        regex = self.get_wildcard_regex("*nscd*")

        self.assertTrue(lines > 1)

    @unimplemented
    def test_ps_a(self):
        """Test `ps -a'"""
        self.command.invoke_uncaught("-a")
        lines = self.output_lines()

        self.assertTrue(lines > 1)

    @unimplemented
    def test_ps_a_wildcard(self):
        """Test `ps -a *nscd*'"""
        self.command.invoke_uncaught("-a *nscd*")
        lines = self.output_lines()

        regex = self.get_wildcard_regex("*nscd*")

        self.assertTrue(lines > 1)

    @unimplemented
    def test_ps_g(self):
        """Test `ps -g'"""
        self.command.invoke_uncaught("-g")
        lines = self.output_lines()

        self.assertTrue(lines > 1)

    @unimplemented
    def test_ps_g_wildcard(self):
        """Test `ps -g *nscd*'"""
        self.command.invoke_uncaught("-g *nscd*")
        lines = self.output_lines()

        regex = self.get_wildcard_regex("*nscd*")

        self.assertTrue(lines > 1)

    @unimplemented
    def test_ps_r(self):
        """Test `ps -r'"""
        self.command.invoke_uncaught("-r")
        lines = self.output_lines()

        self.assertTrue(lines > 1)

    @unimplemented
    def test_ps_r_wildcard(self):
        """Test `ps -r *nscd*'"""
        self.command.invoke_uncaught("-r *nscd*")
        lines = self.output_lines()

        regex = self.get_wildcard_regex("*nscd*")

        self.assertTrue(lines > 1)
