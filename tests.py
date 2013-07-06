#!/usr/bin/python3

import os
from os.path import join, abspath, isfile
import subprocess
import tempfile
import unittest

MAIN_C = """
#include "hello.h"

int main() {
    hello();
    return 0;
}
"""

HELLO_C = """
#include "hello.h"
#include <stdio.h>
void hello() {
    printf("Hello, World");
}
"""

HELLO_H = """
extern void hello();
"""

SUBMAIN_C = """
#include <stdio.h>

int main() {
    printf("Hello, Subworld");
    return 0;
}
"""

class TestCbobCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_dir = tempfile.TemporaryDirectory()
        cls.project_path = cls.project_dir.name
        cls.src_dir = join(cls.project_path, "src")
        cls.bin_dir = join(cls.project_path, "bin")
        cls.sub_dir = join(cls.project_path, "subtest")
        cls.src_files = {join(cls.src_dir, name) for name in ("hello.c", "main.c")}
        cls.sub_files = {join(cls.sub_dir, name) for name in ("submain.c", )}
        cbob_path = abspath("cbob.py") 
        assert(isfile(cbob_path))
        cls.cbob_cmd = ["python3", cbob_path]
        os.makedirs(cls.src_dir)
        os.makedirs(cls.bin_dir)
        os.makedirs(cls.sub_dir)
        with open(join(cls.src_dir, "main.c"), "w") as main_c_file:
            main_c_file.write(MAIN_C)
        with open(join(cls.src_dir, "hello.c"), "w") as hello_c_file:
            hello_c_file.write(HELLO_C)
        with open(join(cls.src_dir, "hello.h"), "w") as hello_h_file:
            hello_h_file.write(HELLO_H)
        with open(join(cls.sub_dir, "submain.c"), "w") as submain_c_file:
            submain_c_file.write(SUBMAIN_C)
        os.chdir(cls.project_path)

    def _call_cmd(self, *args, silent=False):
        cmd = self.cbob_cmd + list(args)
        if silent:
            with open(os.devnull, "w") as null:
                return subprocess.call(cmd, stdout=null, stderr=null)
        else:
            return subprocess.call(cmd)

    def _get_lines_cmd(self, *args):
        cmd = self.cbob_cmd + list(args)
        out = subprocess.check_output(cmd, universal_newlines=True)
        return {line.strip() for line in out.split("\n") if line}

    def _get_err_lines_cmd(self, *args):
        cmd = self.cbob_cmd + list(args)
        with open(os.devnull, "w") as null:
            with subprocess.Popen(cmd, stdout=null, stderr=subprocess.PIPE, universal_newlines=True) as process:
                return process.communicate()[1]


    def test_a1_init(self):
        self.assertEqual(self._call_cmd("init"), 0)

    def test_a2_init_again(self):
        self.assertNotEqual(self._call_cmd("init", silent=True), 0)

    def test_b1_new(self):
        self.assertEqual(self._call_cmd("new", "hello"), 0)

    def test_b2_new_again(self):
        self.assertNotEqual(self._call_cmd("new", "hello", silent=True), 0)

    def test_b3_info(self):
        out_set = self._get_lines_cmd("info")
        self.assertTrue(set(("hello",)) < out_set)

    def test_c_wrong_command(self):
        self.assertNotEqual(self._call_cmd("nonexisting_command", silent=True), 0)

    def test_d1_add(self):
        out_set = self._get_lines_cmd("add", "hello", *self.src_files)
        # If all exists, cbob doesn't say anything
        self.assertEqual(out_set, set())

    def test_d2_show(self):
        out_set = self._get_lines_cmd("show", "hello")
        self.assertTrue(self.src_files < out_set)

    def test_d3_add_nonexisting_file(self):
        err_set = self._get_err_lines_cmd("add", "hello", "i-dont-exists.c")
        # it should complain that this file doesn't exist (otherwise stay silent)
        self.assertNotEqual(err_set, set())

    def test_d4_remove(self):
        self.assertEqual(self._call_cmd("remove", "hello", *self.src_files), 0)

    def test_d5_show_not(self):
        out_set = self._get_lines_cmd("show", "hello")
        self.assertFalse(self.src_files < out_set)

    def test_e1_add_wildcard(self):
        file_wildcard = join("src", "*.c")
        self.assertEqual(self._call_cmd("add", "hello", file_wildcard), 0)

    def test_e2_show_wildcard(self):
        self.test_d2_show()

    def test_f_add_nonexisting_target(self):
        self.assertNotEqual(self._call_cmd("add", "nonexisting_target", *self.src_files, silent=True), 0)

    def test_g1_build(self):
        # it's not configured yet
        self.assertNotEqual(self._call_cmd("build", "hello", silent=True), 0)

    def test_g2_configure_auto(self):
        self.assertEqual(self._call_cmd("configure", "hello", "--auto"), 0)

    def test_g3_build(self):
        self.assertEqual(self._call_cmd("build", "hello"), 0)
    
    def test_g4_build_again(self):
        self.assertEqual(self._call_cmd("build", "hello"), 0)

    def test_g5_run_binary(self):
        cmd = (join(self.bin_dir, "hello"))
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        self.assertEqual(out, "Hello, World")

    def test_g6_clean(self):
        self.assertTrue(isfile(join(self.bin_dir, "hello")))
        self.assertEqual(self._call_cmd("clean", "hello", "-a"), 0)
        self.assertFalse(isfile(join(self.bin_dir, "hello")))

    def test_g7_build_oneshot(self):
        self.assertEqual(self._call_cmd("build", "hello", "--oneshot"), 0)

    def test_g8_run_binary_again(self):
        cmd = (join(self.bin_dir, "hello"))
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        self.assertEqual(out, "Hello, World")

    def test_h1_new_parent(self):
        self.assertEqual(self._call_cmd("new", "all"), 0)

    def test_h2_depend_child(self):
        self.assertEqual(self._call_cmd("depend", "all", "hello"), 0)

    def test_h3_depend_nonexisting_child(self):
        self.assertNotEqual(self._call_cmd("depend", "all", "good-bye", silent=True), 0)

    def test_h4_show_depend(self):
        out_set = self._get_lines_cmd("show", "all", "--dependencies")
        self.assertTrue(set(("hello",)) < out_set)

    def test_h5_build(self):
        self.assertEqual(self._call_cmd("build", "all"), 0)

    def test_i1_subadd(self):
        # subproject is not initialized
        # cbob will not fail, but it won't add it either
        # it will instead issue a warning
        err_set = self._get_err_lines_cmd("subadd", "subtest")
        self.assertNotEqual(err_set, set())

    def test_i2_show_subproject_not(self):
        out_set = self._get_lines_cmd("info", "--subprojects")
        self.assertFalse(set(("subtest",)) < out_set)

    def test_i3_sub_init(self):
        os.chdir(self.sub_dir)
        self.assertEqual(self._call_cmd("init"), 0)
        os.chdir(self.project_path)

    def test_i4_subadd_for_real(self):
        self.assertEqual(self._call_cmd("subadd", "subtest", silent=True), 0)

    def test_i5_show_subproject(self):
        out_set = self._get_lines_cmd("info", "--subprojects")
        self.assertTrue(set(("subtest",)) < out_set)

    def test_i6_sub_init(self):
        os.chdir(self.sub_dir)
        self.assertNotEqual(self._call_cmd("init", silent=True), 0)
        os.chdir(self.project_path)

    def test_i7_sub_new(self):
        self.assertEqual(self._call_cmd("new", "subtest.subhello"), 0)

    def test_i8_sub_new_again(self):
        self.assertNotEqual(self._call_cmd("new", "subtest.subhello", silent=True), 0)

    def test_j1_sub_add(self):
        self.assertEqual(self._call_cmd("add", "subtest.subhello", *self.sub_files), 0)

    def test_j2_sub_add_wrong(self):
        err_set = self._get_err_lines_cmd("add", "subtest.subhello", *self.src_files)
        self.assertNotEqual(err_set, set())

    def test_j3_sub_show(self):
        out_set = self._get_lines_cmd("show", "subtest.subhello")
        self.assertTrue(self.sub_files < out_set)
        self.assertFalse(self.src_files < out_set)

    def test_k1_sub_configure_auto(self):
        self.assertEqual(self._call_cmd("configure", "subtest.subhello", "--auto"), 0)

    def test_k2_sub_build(self):
        self.assertEqual(self._call_cmd("build", "subtest.subhello"), 0)

    def test_k3_sub_run_binary(self):
        cmd = (join(self.sub_dir, "subhello"))
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        self.assertEqual(out, "Hello, Subworld")

    def test_k4_sub_clean(self):
        self.assertTrue(isfile(join(self.sub_dir, "subhello")))
        self.assertEqual(self._call_cmd("clean", "subtest.subhello", "-a"), 0)
        self.assertFalse(isfile(join(self.sub_dir, "subhello")))

    def test_l1_sub_depend(self):
        self.assertEqual(self._call_cmd("depend", "all", "subtest.subhello"), 0)

    def test_l2_build(self):
        self.assertEqual(self._call_cmd("build", "all"), 0)

    def test_l3_sub_run_binary_again(self):
        cmd = (join(self.sub_dir, "subhello"))
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        self.assertEqual(out, "Hello, Subworld")


    @classmethod
    def tearDownClass(cls):
        cls.project_dir.cleanup()

if __name__ == "__main__":
    unittest.main()
