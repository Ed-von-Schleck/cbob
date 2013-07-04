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
        cls.sub_dir = join(cls.project_path, "sub")
        cbob_path = abspath("cbob.py") 
        assert(isfile(cbob_path))
        cls.cbob_cmd = ["python3", cbob_path]
        os.makedirs(cls.src_dir)
        os.makedirs(cls.bin_dir)
        with open(join(cls.src_dir, "main.c"), "w") as main_c_file:
            main_c_file.write(MAIN_C)
        with open(join(cls.src_dir, "hello.c"), "w") as hello_c_file:
            hello_c_file.write(HELLO_C)
        with open(join(cls.src_dir, "hello.h"), "w") as hello_h_file:
            hello_h_file.write(HELLO_H)
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
        file_names = (join(self.src_dir, name) for name in ("hello.c", "main.c"))
        self.assertEqual(self._call_cmd("add", "hello", *file_names), 0)

    def test_d2_show(self):
        file_names = (join(self.src_dir, name) for name in ("hello.c", "main.c"))
        abs_file_paths = {abspath(file_name) for file_name in file_names}
        out_set = self._get_lines_cmd("show", "hello")
        self.assertTrue(abs_file_paths < out_set)

    def test_d3_remove(self):
        file_names = (join(self.src_dir, name) for name in ("hello.c", "main.c"))
        self.assertEqual(self._call_cmd("remove", "hello", *file_names), 0)

    def test_d4_show_not(self):
        file_names = (join(self.src_dir, name) for name in ("hello.c", "main.c"))
        abs_file_paths = {abspath(file_name) for file_name in file_names}
        out_set = self._get_lines_cmd("show", "hello")
        self.assertFalse(abs_file_paths < out_set)

    def test_e1_add_wildcard(self):
        file_wildcard = join("src", "*.c")
        self.assertEqual(self._call_cmd("add", "hello", file_wildcard), 0)

    def test_e2_show_wildcard(self):
        self.test_d2_show()

    def test_f_add_nonexisting_target(self):
        files = (join(self.src_dir, name) for name in ("hello.c", "main.c"))
        self.assertNotEqual(self._call_cmd("add", "nonexisting_target", *files, silent=True), 0)

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
        self.assertEqual(self._call_cmd("clean", "hello", "-a"), 0)

    def test_g7_build_once_again(self):
        self.assertEqual(self._call_cmd("build", "hello"), 0)

    def test_g8_run_binary_again(self):
        cmd = (join(self.bin_dir, "hello"))
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        self.assertEqual(out, "Hello, World")

    def test_h1_new_parent(self):
        self.assertEqual(self._call_cmd("new", "all"), 0)

    def test_h2_depend_child(self):
        self.assertEqual(self._call_cmd("depend", "all", "hello"), 0)

    def test_h3_show_depend(self):
        out_set = self._get_lines_cmd("show", "all", "--dependencies")
        self.assertTrue(set(("hello",)) < out_set)

    def test_h4_build(self):
        self.assertEqual(self._call_cmd("build", "all"), 0)


    @classmethod
    def tearDownClass(cls):
        cls.project_dir.cleanup()

if __name__ == "__main__":
    unittest.main()
