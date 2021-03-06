#!/usr/bin/python3

import os
from os.path import join, abspath, isfile
import subprocess
import tempfile
import unittest

MAIN_C = """
#include "../include/hello.h"

int main() {
    hello();
    return 0;
}
"""

HELLO_C = """
#include "../include/hello.h"
#include "../include/constants.h"

#include <stdio.h>

void hello() {
    printf(HELLO_WORLD);
}
"""

CONSTANTS_H = """
#define HELLO_WORLD "Hello, World"
"""

HELLO_H = """
extern void hello();
"""

ERROR_C = """
#error
"""

SUBMAIN_C = """
#include <stdio.h>

int main() {
    printf("Hello, Subworld");
    return 0;
}
"""

PRE_BUILD_PY = """
def pre_build(target):
    print("Hello pre-build")
"""

POST_BUILD_PY = """
def post_build(target):
    print("Hello post-build")
"""

class TestCbobCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_dir = tempfile.TemporaryDirectory()
        cls.project_path = cls.project_dir.name

        cbob_path = abspath("cbob.py") 
        assert(isfile(cbob_path))
        cls.cbob_cmd = ["python3", cbob_path]

        files = {
            "src": {
                "hello.c": HELLO_C,
                "main.c": MAIN_C,
            },
            "include": {
                "hello.h": HELLO_H,
                "constants.h": CONSTANTS_H,
            },
            "bin": {
            },
            "subtest": {
                "submain.c": SUBMAIN_C,
            },
            "plugins": {
                "prebuild.py": PRE_BUILD_PY,
                "postbuild.py": POST_BUILD_PY
            },
            "error": {
                "error.c": ERROR_C
            }
        }

        cls.files = {}

        for rel_dirname, files in files.items():
            abs_dirname = join(cls.project_path, rel_dirname)
            os.makedirs(abs_dirname)
            cls.files[rel_dirname] = {}
            for filename, content in files.items():
                abs_filepath = join(abs_dirname, filename)
                with open(abs_filepath, "w") as f:
                    f.write(content)
                cls.files[rel_dirname][filename] = abs_filepath

        cls.bin_dir = join(cls.project_path, "bin")
        cls.sub_dir = join(cls.project_path, "subtest")

        os.chdir(cls.project_path)

    def _call_cmd(self, *args, silent=False):
        cmd = self.cbob_cmd + list(args)
        if silent:
            with open(os.devnull, "w") as null:
                return subprocess.call(cmd, stdout=null, stderr=null)
        else:
            return subprocess.call(cmd)

    def _get_words_cmd(self, *args):
        cmd = self.cbob_cmd + list(args)
        out = subprocess.check_output(cmd, universal_newlines=True)
        return {line.strip() for line in out.split() if line}

    def _get_err_words_cmd(self, *args):
        cmd = self.cbob_cmd + list(args)
        with open(os.devnull, "w") as null:
            with subprocess.Popen(cmd, stdout=null, stderr=subprocess.PIPE, universal_newlines=True) as process:
                out = process.communicate()[1]
                return {line.strip() for line in out.split() if line}


    def test_a1_init(self):
        self.assertEqual(self._call_cmd("init"), 0)
        self.assertNotEqual(self._call_cmd("init", silent=True), 0)

    def test_b1_new(self):
        self.assertEqual(self._call_cmd("new", "hello"), 0)
        self.assertNotEqual(self._call_cmd("new", "hello", silent=True), 0)

    def test_b3_info(self):
        out_set = self._get_words_cmd("info")
        self.assertTrue(set(("hello",)) < out_set)

    def test_c_wrong_command(self):
        self.assertNotEqual(self._call_cmd("nonexisting_command", silent=True), 0)

    def test_d1_add(self):
        out_set = self._get_words_cmd("add", "--target", "hello", *self.files["src"].values())
        # If all files exist, cbob doesn't say anything
        self.assertEqual(out_set, set())

    def test_d2_list(self):
        out_set = self._get_words_cmd("list", "--target", "hello")
        self.assertTrue(set(self.files["src"].values()) < out_set)

    def test_d3_add_nonexisting_file(self):
        err_set = self._get_err_words_cmd("add", "--target", "hello", "i-dont-exists.c")
        # it should complain that this file doesn't exist (otherwise stay silent)
        self.assertNotEqual(err_set, set())

    def test_d4_remove(self):
        self.assertEqual(self._call_cmd("remove", "--target", "hello", *self.files["src"].values()), 0)

    def test_d5_list_not(self):
        out_set = self._get_words_cmd("list", "--target", "hello")
        self.assertFalse(set(self.files["src"].values()) < out_set)

    def test_e1_add_wildcard(self):
        file_wildcard = join("src", "*.c")
        self.assertEqual(self._call_cmd("add", "--target", "hello", file_wildcard), 0)
        file_wildcard = join("error", "*.c")
        self.assertEqual(self._call_cmd("add", "--target", "hello", file_wildcard), 0)

    def test_e2_list_wildcard(self):
        # This adds the "error.c" file as well
        out_set = self._get_words_cmd("list", "--target", "hello")
        self.assertTrue(set(self.files["src"].values()) < out_set)
        self.assertTrue(set(self.files["error"].values()) < out_set)

    def test_f1_add_nonexisting_target(self):
        self.assertNotEqual(self._call_cmd("add", "--target", "nonexisting_target", *self.files["src"].values(), silent=True), 0)

    def test_g1_build_fail(self):
        # it's not configured yet
        self.assertNotEqual(self._call_cmd("build", "--target", "hello", silent=True), 0)
        self.assertEqual(self._call_cmd("configure", "--target", "hello", "--auto"), 0)
        # it has the error file in it
        self.assertNotEqual(self._call_cmd("build", "--target", "hello", silent=True), 0)
        self.assertEqual(self._call_cmd("remove", "--target", "hello", *self.files["error"].values()), 0)
    
    def test_g5_build_default(self):
        # target 'hello' should be the default target
        self.assertEqual(self._call_cmd("build"), 0)

    def test_g6_run_binary(self):
        cmd = (join(self.bin_dir, "hello"))
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        self.assertEqual(out, "Hello, World")

    def test_g7_clean(self):
        self.assertTrue(isfile(join(self.bin_dir, "hello")))
        self.assertEqual(self._call_cmd("clean", "--target", "hello", "-a"), 0)
        self.assertFalse(isfile(join(self.bin_dir, "hello")))

    def test_g8_build(self):
        out_set = self._get_err_words_cmd("--debug", "build", "--target", "hello")
        # Check that all sources are mentioned in the debug output
        self.assertTrue(set(self.files["src"].values()) < out_set)

        out_set = self._get_err_words_cmd("--debug", "build", "--target", "hello")
        # Check that no source is mentioned in the debug output, since they didn't change
        self.assertFalse(set(self.files["src"].values()) < out_set)

        src_file_list = list(self.files["src"].values())
        subprocess.call(("touch", src_file_list[0]))
        out_set = self._get_err_words_cmd("--debug", "build", "--target", "hello")
        # Check that just the one source file that we touched is recompiled
        self.assertTrue(set(src_file_list[0:1]) < out_set)
        self.assertFalse(set(src_file_list[1:]) < out_set)

        #header_file_list = list(self.files["include"])
        for header_file in self.files["include"].values():
            subprocess.call(("touch", header_file))
        out_set = self._get_err_words_cmd("--debug", "build", "--target", "hello")
        # Check that all sources (that depend on the header file) are recompiled
        self.assertTrue(set(self.files["src"].values()) < out_set)

    def test_g9_run_binary_again(self):
        cmd = (join(self.bin_dir, "hello"))
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        self.assertEqual(out, "Hello, World")

    def test_h1_new_parent(self):
        self.assertEqual(self._call_cmd("new", "all"), 0)

    def test_h2_depend_child(self):
        self.assertEqual(self._call_cmd("dependencies", "add", "--target", "all", "hello"), 0)
        err_set = self._get_err_words_cmd("-v", "dependencies", "add", "--target", "all", "hello")
        self.assertNotEqual(err_set, set())
        err_set = self._get_err_words_cmd("dependencies", "add", "--target", "all", "good-bye")
        self.assertNotEqual(err_set, set())

        out_set = self._get_words_cmd("dependencies", "list", "--target", "all")
        self.assertTrue(set(("hello",)) < out_set)

    def test_h5_build(self):
        self.assertEqual(self._call_cmd("build", "--target", "all"), 0)

    def test_h7_depend_remove(self):
        self.assertEqual(self._call_cmd("dependencies", "remove", "--target", "all", "hello"), 0)
        err_set = self._get_err_words_cmd("-v", "dependencies", "remove", "--target", "all", "hello")
        self.assertNotEqual(err_set, set())

        out_set = self._get_words_cmd("dependencies", "list", "--target", "all")
        self.assertFalse(set(("hello",)) < out_set)


    def test_i1_subadd(self):
        # subproject is not initialized
        # cbob will not fail, but it won't add it either
        # it will instead issue a warning
        err_set = self._get_err_words_cmd("subprojects", "add", "subtest")
        self.assertNotEqual(err_set, set())
        out_set = self._get_words_cmd("info", "--subprojects")
        self.assertFalse(set(("subtest",)) < out_set)

    def test_i3_sub_init(self):
        os.chdir(self.sub_dir)
        self.assertEqual(self._call_cmd("init"), 0)
        os.chdir(self.project_path)

    def test_i4_subadd_for_real(self):
        self.assertEqual(self._call_cmd("subprojects", "add", "subtest"), 0)
        out_set = self._get_words_cmd("info", "--subprojects")
        self.assertTrue(set(("subtest",)) < out_set)

    def test_i6_sub_init(self):
        os.chdir(self.sub_dir)
        self.assertNotEqual(self._call_cmd("init", silent=True), 0)
        os.chdir(self.project_path)

    def test_i7_sub_new(self):
        self.assertEqual(self._call_cmd("new", "subtest.subhello"), 0)
        self.assertNotEqual(self._call_cmd("new", "subtest.subhello", silent=True), 0)

    def test_j1_sub_add(self):
        self.assertEqual(self._call_cmd("add", "--target", "subtest.subhello", *self.files["subtest"].values()), 0)

        err_set = self._get_err_words_cmd("add", "--target", "subtest.subhello", *self.files["src"].values())
        self.assertNotEqual(err_set, set())

    def test_j3_sub_list(self):
        out_set = self._get_words_cmd("list", "--target", "subtest.subhello")
        self.assertTrue(set(self.files["subtest"].values()) < out_set)
        self.assertFalse(set(self.files["src"].values()) < out_set)

    def test_k1_sub_configure_auto(self):
        self.assertEqual(self._call_cmd("configure", "--target", "subtest.subhello", "--auto"), 0)

    def test_k2_sub_build(self):
        self.assertEqual(self._call_cmd("build", "--target", "subtest.subhello"), 0)

    def test_k3_sub_run_binary(self):
        cmd = (join(self.sub_dir, "subhello"))
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        self.assertEqual(out, "Hello, Subworld")

    def test_k4_sub_clean(self):
        self.assertTrue(isfile(join(self.sub_dir, "subhello")))
        self.assertEqual(self._call_cmd("clean", "--target", "subtest.subhello", "-a"), 0)
        self.assertFalse(isfile(join(self.sub_dir, "subhello")))

    def test_l1_sub_depend(self):
        self.assertEqual(self._call_cmd("dependencies", "add", "--target", "all", "subtest.subhello"), 0)

    def test_l2_build(self):
        self.assertEqual(self._call_cmd("build", "--target", "all"), 0)

    def test_l3_sub_run_binary_again(self):
        cmd = (join(self.sub_dir, "subhello"))
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        self.assertEqual(out, "Hello, Subworld")

    def test_l5_remove_sub(self):
        self.assertEqual(self._call_cmd("subprojects", "remove", self.sub_dir), 0)
        # cbob should complain if the subproject doesn't exist
        err_set = self._get_err_words_cmd("subprojects", "remove", "subtest")
        self.assertNotEqual(err_set, set())


    def test_m1_new_error(self):
        self.assertEqual(self._call_cmd("new", "error"), 0)
        self.assertEqual(self._call_cmd("add", "--target", "error", *self.files["error"].values()), 0)
        self.assertNotEqual(self._call_cmd("build", "--target", "error", silent=True), 0)

    def test_n1_plugins(self):
        # first test that default target builds
        self.assertEqual(self._call_cmd("build"), 0)
        for plugin in self.files["plugins"].values():
            self.assertEqual(self._call_cmd("plugins", "add", plugin), 0)
        for plugin in self.files["plugins"].values():
            # cbob should complain if we try to add the same plugin twice
            err_set = self._get_err_words_cmd("plugins", "add", plugin)
            self.assertNotEqual(err_set, set())
        out_set = self._get_words_cmd("build")
        self.assertTrue({"Hello", "pre-build"} < out_set)
        self.assertTrue({"Hello", "post-build"} < out_set)
        out_set = self._get_words_cmd("plugins", "list")
        self.assertTrue(set(self.files["plugins"].values()) < out_set)

        for plugin in self.files["plugins"].values():
            self.assertEqual(self._call_cmd("plugins", "remove", plugin), 0)
        for plugin in self.files["plugins"].values():
            # cbob should complain if we try to remove the same plugin twice
            err_set = self._get_err_words_cmd("plugins", "remove", plugin)
            self.assertNotEqual(err_set, set())
        out_set = self._get_words_cmd("build")
        self.assertFalse({"Hello", "pre-build"} < out_set)
        self.assertFalse({"Hello", "post-build"} < out_set)
        out_set = self._get_words_cmd("plugins", "list")
        self.assertFalse(set(self.files["plugins"].values()) < out_set)
        


    @classmethod
    def tearDownClass(cls):
        cls.project_dir.cleanup()

if __name__ == "__main__":
    unittest.main()
