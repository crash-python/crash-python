# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
import unittest
import gdb

import crash.subsystem.filesystem as fs 

class TestSubsystemFilesystem(unittest.TestCase):
    def get_bits(self, mode):
        v = gdb.Value(mode)
        return fs.inode_mode_permission_bits(v)

    def test_mode_regular_file(self):
        mode = fs.S_IFREG
        self.assertFalse(fs.S_ISLNK(mode))
        self.assertTrue(fs.S_ISREG(mode))
        self.assertFalse(fs.S_ISDIR(mode))
        self.assertFalse(fs.S_ISCHR(mode))
        self.assertFalse(fs.S_ISBLK(mode))
        self.assertFalse(fs.S_ISFIFO(mode))
        self.assertFalse(fs.S_ISSOCK(mode))

    def test_mode_symbolic_link(self):
        mode = fs.S_IFLNK
        self.assertTrue(fs.S_ISLNK(mode))
        self.assertFalse(fs.S_ISREG(mode))
        self.assertFalse(fs.S_ISDIR(mode))
        self.assertFalse(fs.S_ISCHR(mode))
        self.assertFalse(fs.S_ISBLK(mode))
        self.assertFalse(fs.S_ISFIFO(mode))
        self.assertFalse(fs.S_ISSOCK(mode))

    def test_mode_directory(self):
        mode = fs.S_IFDIR
        self.assertFalse(fs.S_ISLNK(mode))
        self.assertFalse(fs.S_ISREG(mode))
        self.assertTrue(fs.S_ISDIR(mode))
        self.assertFalse(fs.S_ISCHR(mode))
        self.assertFalse(fs.S_ISBLK(mode))
        self.assertFalse(fs.S_ISFIFO(mode))
        self.assertFalse(fs.S_ISSOCK(mode))

    def test_mode_chardev(self):
        mode = fs.S_IFCHR
        self.assertFalse(fs.S_ISLNK(mode))
        self.assertFalse(fs.S_ISREG(mode))
        self.assertFalse(fs.S_ISDIR(mode))
        self.assertTrue(fs.S_ISCHR(mode))
        self.assertFalse(fs.S_ISBLK(mode))
        self.assertFalse(fs.S_ISFIFO(mode))
        self.assertFalse(fs.S_ISSOCK(mode))

    def test_mode_blockdev(self):
        mode = fs.S_IFBLK
        self.assertFalse(fs.S_ISLNK(mode))
        self.assertFalse(fs.S_ISREG(mode))
        self.assertFalse(fs.S_ISDIR(mode))
        self.assertFalse(fs.S_ISCHR(mode))
        self.assertTrue(fs.S_ISBLK(mode))
        self.assertFalse(fs.S_ISFIFO(mode))
        self.assertFalse(fs.S_ISSOCK(mode))

    def test_mode_fifo(self):
        mode = fs.S_IFIFO
        self.assertFalse(fs.S_ISLNK(mode))
        self.assertFalse(fs.S_ISREG(mode))
        self.assertFalse(fs.S_ISDIR(mode))
        self.assertFalse(fs.S_ISCHR(mode))
        self.assertFalse(fs.S_ISBLK(mode))
        self.assertTrue(fs.S_ISFIFO(mode))
        self.assertFalse(fs.S_ISSOCK(mode))

    def test_mode_socket(self):
        mode = fs.S_IFSOCK
        self.assertFalse(fs.S_ISLNK(mode))
        self.assertFalse(fs.S_ISREG(mode))
        self.assertFalse(fs.S_ISDIR(mode))
        self.assertFalse(fs.S_ISCHR(mode))
        self.assertFalse(fs.S_ISBLK(mode))
        self.assertFalse(fs.S_ISFIFO(mode))
        self.assertTrue(fs.S_ISSOCK(mode))

    def test_inode_permission_bits_0________(self):
        mode = 0
        perms = self.get_bits(mode)
        self.assertTrue(perms == '?---------')

    def test_inode_permission_bits__________(self):
        mode = fs.S_IFREG
        perms = self.get_bits(mode)
        self.assertTrue(perms == '----------')

    def test_inode_permission_bits__r________(self):
        mode = fs.S_IFREG|fs.S_IRUSR
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-r--------')

    def test_inode_permission_bits___w_______(self):
        mode = fs.S_IFREG|fs.S_IWUSR
        perms = self.get_bits(mode)
        self.assertTrue(perms == '--w-------')

    def test_inode_permission_bits___x______(self):
        mode = fs.S_IFREG|fs.S_IXUSR
        perms = self.get_bits(mode)
        self.assertTrue(perms == '---x------')

    def test_inode_permission_bits__rw_______(self):
        mode = fs.S_IFREG|fs.S_IRUSR|fs.S_IWUSR
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-rw-------')

    def test_inode_permission_bits__r_x______(self):
        mode = fs.S_IFREG|fs.S_IRUSR|fs.S_IXUSR
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-r-x------')

    def test_inode_permission_bits__rwx______(self):
        mode = fs.S_IFREG|fs.S_IRUSR|fs.S_IWUSR|fs.S_IXUSR
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-rwx------')

    def test_inode_permission_bits_____r_____(self):
        mode = fs.S_IFREG|fs.S_IRGRP
        perms = self.get_bits(mode)
        self.assertTrue(perms == '----r-----')

    def test_inode_permission_bits______w____(self):
        mode = fs.S_IFREG|fs.S_IWGRP
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-----w----')

    def test_inode_permission_bits______x___(self):
        mode = fs.S_IFREG|fs.S_IXGRP
        perms = self.get_bits(mode)
        self.assertTrue(perms == '------x---')

    def test_inode_permission_bits_____rw____(self):
        mode = fs.S_IFREG|fs.S_IRGRP|fs.S_IWGRP
        perms = self.get_bits(mode)
        self.assertTrue(perms == '----rw----')

    def test_inode_permission_bits_____r_x___(self):
        mode = fs.S_IFREG|fs.S_IRGRP|fs.S_IXGRP
        perms = self.get_bits(mode)
        self.assertTrue(perms == '----r-x---')

    def test_inode_permission_bits_____rwx___(self):
        mode = fs.S_IFREG|fs.S_IRGRP|fs.S_IWGRP|fs.S_IXGRP
        perms = self.get_bits(mode)
        self.assertTrue(perms == '----rwx---')

    def test_inode_permission_bits________r__(self):
        mode = fs.S_IFREG|fs.S_IROTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-------r--')

    def test_inode_permission_bits_________w_(self):
        mode = fs.S_IFREG|fs.S_IWOTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '--------w-')

    def test_inode_permission_bits_________x(self):
        mode = fs.S_IFREG|fs.S_IXOTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '---------x')

    def test_inode_permission_bits________rw_(self):
        mode = fs.S_IFREG|fs.S_IROTH|fs.S_IWOTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-------rw-')

    def test_inode_permission_bits________r_x(self):
        mode = fs.S_IFREG|fs.S_IROTH|fs.S_IXOTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-------r-x')

    def test_inode_permission_bits________rwx(self):
        mode = fs.S_IFREG|fs.S_IROTH|fs.S_IWOTH|fs.S_IXOTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-------rwx')

    def test_inode_permission_bits__rw_r__r__(self):
        mode = fs.S_IFREG|fs.S_IRUSR|fs.S_IWUSR|fs.S_IRGRP|fs.S_IROTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-rw-r--r--')

    def test_inode_permission_bits_drw_r__r__(self):
        mode = fs.S_IFDIR|fs.S_IRUSR|fs.S_IWUSR|fs.S_IXUSR
        mode |= fs.S_IRGRP|fs.S_IXGRP|fs.S_IROTH|fs.S_IXOTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == 'drwxr-xr-x')

    def test_inode_permission_bits_srw_r__r__(self):
        mode = fs.S_IFSOCK|fs.S_IRUSR|fs.S_IWUSR|fs.S_IRGRP|fs.S_IROTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == 'srw-r--r--')

    def test_inode_permission_bits_brw_r__r__(self):
        mode = fs.S_IFBLK|fs.S_IRUSR|fs.S_IWUSR|fs.S_IRGRP|fs.S_IROTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == 'brw-r--r--')

    def test_inode_permission_bits_crw_r__r__(self):
        mode = fs.S_IFCHR|fs.S_IRUSR|fs.S_IWUSR|fs.S_IRGRP|fs.S_IROTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == 'crw-r--r--')

    def test_inode_permission_bits_lrwxrwxrwx(self):
        mode = fs.S_IFLNK
        mode |= fs.S_IRUSR|fs.S_IWUSR|fs.S_IXUSR
        mode |= fs.S_IRGRP|fs.S_IWGRP|fs.S_IXGRP
        mode |= fs.S_IROTH|fs.S_IWOTH|fs.S_IXOTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == 'lrwxrwxrwx')

    def test_inode_permission_bits_prw_r__r__(self):
        mode = fs.S_IFIFO|fs.S_IRUSR|fs.S_IWUSR|fs.S_IRGRP|fs.S_IROTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == 'prw-r--r--')

    def test_inode_permission_bits__rwsr_xr_x(self):
        mode = fs.S_IFREG|fs.S_IRUSR|fs.S_IWUSR|fs.S_IXUSR|fs.S_ISUID
        mode |= fs.S_IRGRP|fs.S_IXGRP|fs.S_IROTH|fs.S_IXOTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-rwsr-xr-x')

    def test_inode_permission_bits__rwSr__r__(self):
        mode = fs.S_IFREG|fs.S_IRUSR|fs.S_IWUSR|fs.S_ISUID
        mode |= fs.S_IRGRP|fs.S_IROTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-rwSr--r--')

    def test_inode_permission_bits__rwxr_sr_x(self):
        mode = fs.S_IFREG|fs.S_IRUSR|fs.S_IWUSR|fs.S_IXUSR
        mode |= fs.S_IRGRP|fs.S_IXGRP|fs.S_ISGID|fs.S_IROTH|fs.S_IXOTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-rwxr-sr-x')

    def test_inode_permission_bits__rw_r_Sr__(self):
        mode = fs.S_IFREG|fs.S_IRUSR|fs.S_IWUSR
        mode |= fs.S_IRGRP|fs.S_ISGID|fs.S_IROTH
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-rw-r-Sr--')

    def test_inode_permission_bits_drwxrwxrwt(self):
        mode = fs.S_IFDIR|fs.S_IRUSR|fs.S_IWUSR|fs.S_IXUSR
        mode |= fs.S_IRGRP|fs.S_IWGRP|fs.S_IXGRP
        mode |= fs.S_IROTH|fs.S_IWOTH|fs.S_IXOTH|fs.S_ISVTX
        perms = self.get_bits(mode)
        self.assertTrue(perms == 'drwxrwxrwt')

    def test_inode_permission_bits__rw_r__r_T(self):
        mode = fs.S_IFREG|fs.S_IRUSR|fs.S_IWUSR
        mode |= fs.S_IRGRP|fs.S_IROTH|fs.S_ISVTX
        perms = self.get_bits(mode)
        self.assertTrue(perms == '-rw-r--r-T')
