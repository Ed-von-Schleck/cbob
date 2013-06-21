import os
import os.path

def get_project_root():
    if not hasattr(get_project_root, "_project_root"):
        path = os.getcwd()
        oldpath = ""
        while path != oldpath:
            oldpath = path
            if os.path.isdir(os.path.join(path, ".cbob")):
                get_project_root._project_root = path
                break
            path = os.path.dirname(path)
        else:
            get_project_root._project_root = None
    return get_project_root._project_root

def get_cbob_dir():
    project_root = get_project_root()
    return None if project_root is None else os.path.join(project_root, ".cbob")

def get_targets_dir():
    project_root = get_project_root()
    return None if project_root is None else os.path.join(project_root, ".cbob", "targets")

def get_target_dir(target_name):
    targets_dir = get_targets_dir()
    return None if targets_dir is None else os.path.join(targets_dir, target_name)

def get_sources_dir(target_name):
    target_dir = get_target_dir(target_name)
    return None if target_dir is None else os.path.join(target_dir, "sources")

def get_build_dir(target_name):
    project_root = get_project_root()
    return None if project_root is None else os.path.join(project_root, ".cbob", ".build")

def get_compiler_symlink(target_name):
    target_dir = get_target_dir(target_name)
    return None if target_dir is None else os.path.join(target_dir, "compiler")

def get_linker_symlink(target_name):
    target_dir = get_target_dir(target_name)
    return None if target_dir is None else os.path.join(target_dir, "linker")

def get_bindir_symlink(target_name):
    target_dir = get_target_dir(target_name)
    return None if target_dir is None else os.path.join(target_dir, "bindir")

def get_gcc_path():
    import subprocess
    return subprocess.check_output(["which", "gcc"]).strip()
