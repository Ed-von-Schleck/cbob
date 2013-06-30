import os
import os.path
import subprocess

import cbob.checks as checks
import cbob.pathhelpers as pathhelpers

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

@checks.requires_target_exists
def configure(target_name, auto, force, compiler, linker, bindir):
    target_dir = pathhelpers.get_target_dir(target_name)

    compiler_symlink_path = pathhelpers.get_compiler_symlink(target_name)
    compiler_symlink_exists = os.path.islink(compiler_symlink_path) 

    linker_symlink_path = pathhelpers.get_linker_symlink(target_name)
    linker_symlink_exists = os.path.islink(linker_symlink_path) 

    bindir_symlink_path = pathhelpers.get_bindir_symlink(target_name)
    bindir_symlink_exists = os.path.islink(bindir_symlink_path)

    project_root = pathhelpers.get_project_root()

    if auto:
        if compiler is None:
            if compiler_symlink_exists and not force:
                print("WARNING: There's already a compiler configured ({}).".format(os.readlink(compiler_symlink_path)))
                print("Use '--force' to force overwriting previous configurations.")
            else:
                lang = _guess_target_language(target_name)
                compiler_path = None
                if lang is None:
                    print("ERROR: Language could not be determined. Please configure compiler manually.")
                    print("(cbob configure --compiler <path-to-compiler>)")

                #TODO: enable support for other compilers
                if lang == "C":
                    compiler_path = subprocess.check_output(["which", "gcc"]).strip()
                elif lang == "C++":
                    compiler_path = subprocess.check_output(["which", "g++"]).strip()

                #TODO: check that 'compiler_path' is actually sane.

                if compiler_path is not None:
                    if compiler_symlink_exists and force:
                        os.unlink(compiler_symlink_path)
                    os.symlink(compiler_path, compiler_symlink_path)
                    print("Determined language of target '{}' to be '{}'. The chosen compiler is '{}'.".format(target_name, lang, compiler_path.decode("utf-8")))
                    print("Please configure manually if that is incorrect ('cbob configure --compiler <path-to-compiler>').")
        if linker is None:
            if linker_symlink_exists and not force:
                print("WARNING: There's already a linker configured ({}).".format(os.readlink(linker_symlink_path)))
                print("Use '--force' to force overwriting previous configurations.")
            else:
                linker_path = compiler_path
                if linker_symlink_exists and force:
                    os.unlink(linker_symlink_path)
                os.symlink(linker_path, linker_symlink_path)
                print("The chosen linker for target '{}' is '{}'.".format(target_name, linker_path.decode("utf-8")))
                print("Please configure manually if that is incorrect ('cbob configure --linker <path-to-linker>').")
        if bindir is None:
            if bindir_symlink_exists and not force:
                print("WARNING: There's already a output directory for binaries configured ({}).".format(os.readlink(bindir_symlink_path)))
                print("Use '--force' to force overwriting previous configurations.")
            else:
                if bindir_symlink_exists and force:
                    os.unlink(bindir_symlink_path)
                assumed_bindir = os.path.join(project_root, "bin")
                bindir_auto = assumed_bindir if os.path.isdir(assumed_bindir) else project_root
                os.symlink(bindir_auto, bindir_symlink_path)
    else: # manual configuration
        if compiler is not None:
            os.symlink(compiler, compiler_symlink_path)
        if linker is not None:
            os.symlink(linker, linker_symlink_path)
        if bindir is not None:
            os.symlink(bindir, bindir_symlink_path)
