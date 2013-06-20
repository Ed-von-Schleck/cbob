import os
import os.path
import subprocess

import src.checks as checks
import src.pathhelpers as pathhelpers

def _guess_target_language(target_name):
    sources_dir = pathhelpers.get_sources_dir(target_name)
    for file_name in os.listdir(sources_dir):
        root, ext = os.path.splitext(file_name)
        ext = ext.lower()
        if ext == ".c":
            return "C"
        elif ext in (".cc", ".cpp", "c++", ".cxx"):
            return "C++"
    return None

@checks.requires_initialized
def configure(target_name, auto):
    checks.check_target_exists(target_name)
    target_dir = pathhelpers.get_target_dir(target_name)
    if auto:
        lang = _guess_target_language(target_name)
        if lang is None:
            print("ERROR: Language could not be determined. Please configure manually.")
            exit(1)
        elif lang == "C":
            compiler_path = subprocess.check_output(["which", "gcc"])
        elif lang == "C++":
            compiler_path = subprocess.check_output(["which", "g++"])

        compiler_path = compiler_path.strip()
        print("Determined language of target '{}' to be '{}'. The chosen compiler is '{}'.".format(target_name, lang, compiler_path.decode("utf-8")))
        print("Please configure manually if that is incorrect.")

        os.symlink(compiler_path, os.path.join(target_dir, "compiler"))

            


