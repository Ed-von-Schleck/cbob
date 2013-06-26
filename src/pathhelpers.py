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

def get_objects_dir(target_name):
    target_dir = get_target_dir(target_name)
    return None if target_dir is None else os.path.join(target_dir, "objects")

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

def mangle_path(path):
    project_root = get_project_root()
    abs_actual_file_path = os.path.abspath(path)
    norm_actual_file_path = os.path.normpath(os.path.relpath(abs_actual_file_path, project_root))
    return norm_actual_file_path.replace(os.sep, "_")

def demangle_path_rel(mangled_path):
    return mangled_path.replace("_", os.sep)

def demangle_path_abs(mangled_path):
    path_rel = demangle_path_rel(mangled_path)
    return os.path.join(project_root, path_rel)

def get_object_file_path(target_name, path):
    mangled_file_name = mangle_path(path)
    objects_dir = get_objects_dir(target_name)
    return None if objects_dir is None else os.path.join(objects_dir, os.path.splitext(mangled_file_name)[0] + ".o")

def get_deps_file_path(target_name):
    target_dir = get_target_dir(target_name)
    return None if target_dir is None else os.path.join(target_dir, "deps")

def get_source_path_from_symlink(target_name, symlink_path):
    sources_dir = get_sources_dir(target_name)
    return os.path.normpath(os.path.join(sources_dir, os.readlink(os.path.join(sources_dir, symlink_path))))
