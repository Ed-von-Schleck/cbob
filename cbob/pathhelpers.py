import collections
import os
import os.path

SubprojectTarget = collections.namedtuple("SubprojectTarget", ("subprojects", "target")) 

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

def get_subprojects_dir(subproject_names=None):
    if not subproject_names:
        project_root = get_project_root()
    else:
        project_root = get_subprojects_dir(subproject_names)
    return None if project_root is None else os.path.join(project_root, ".cbob", "subprojects")

def get_subproject_root(subproject_names):
    subprojects_dir = get_subprojects_dir(subprojects_dir[1:])
    return None if subprojects_dir is None else os.readlink(os.path.join(subprojects_dir, subproject_names))

def split_subprojects_target(dottet_target_name):
    splitted = dottet_target_name.split(".")
    subproject_target = SubprojectTarget(splitted[0:-1] if splitted[0:-1] else None, splitted[-1])
    return subproject_target

def get_cbob_dir(subproject_names=None):
    project_root = get_project_root() if subproject_names is None else get_subproject_root(subproject_names)
    return None if project_root is None else os.path.join(project_root, ".cbob")

def get_targets_dir(subproject_names=None):
    project_root = get_project_root() if subproject_names is None else get_subproject_root(subproject_names)
    return None if project_root is None else os.path.join(project_root, ".cbob", "targets")

def get_target_dir(target_name, subproject_names=None):
    targets_dir = get_targets_dir(subproject_names)
    return None if targets_dir is None else os.path.join(targets_dir, target_name)

def get_sources_dir(target_name, subproject_names=None):
    target_dir = get_target_dir(target_name, subproject_names)
    return None if target_dir is None else os.path.join(target_dir, "sources")

def get_objects_dir(target_name, subproject_names=None):
    target_dir = get_target_dir(target_name, subproject_names)
    return None if target_dir is None else os.path.join(target_dir, "objects")

def get_compiler_symlink(target_name, subproject_names=None):
    target_dir = get_target_dir(target_name, subproject_names)
    return None if target_dir is None else os.path.join(target_dir, "compiler")

def get_linker_symlink(target_name, subproject_names=None):
    target_dir = get_target_dir(target_name, subproject_names)
    return None if target_dir is None else os.path.join(target_dir, "linker")

def get_bindir_symlink(target_name, subproject_names=None):
    target_dir = get_target_dir(target_name, subproject_names)
    return None if target_dir is None else os.path.join(target_dir, "bindir")

def get_gcc_path():
    import subprocess
    return subprocess.check_output(["which", "gcc"], universal_newlines=True).strip()

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

def get_object_file_path(target_name, path, subproject_names=None):
    mangled_file_name = mangle_path(path)
    objects_dir = get_objects_dir(target_name, subproject_names)
    return None if objects_dir is None else os.path.join(objects_dir, os.path.splitext(mangled_file_name)[0] + ".o")

def get_deps_file_path(target_name, subproject_names=None):
    target_dir = get_target_dir(target_name, subproject_names)
    return None if target_dir is None else os.path.join(target_dir, "deps")

def get_source_path_from_symlink(target_name, symlink_path, subproject_names=None):
    sources_dir = get_sources_dir(target_name, subproject_names)
    return os.path.normpath(os.path.join(sources_dir, os.readlink(os.path.join(sources_dir, symlink_path))))

def get_bin_path(target_name, subproject_names=None):
    bindir = get_bindir_symlink(target_name, subproject_names)
    return None if bindir is None else os.path.join(os.readlink(bindir), target_name)

def get_precompiled_headers_dir(target_name, subproject_names=None):
    target_dir = get_target_dir(target_name, subproject_names)
    return None if target_dir is None else os.path.join(target_dir, "precompiled_headers")

def get_uncompiled_header_path(target_name, path, subproject_names=None):
    mangled_file_name = mangle_path(path)
    precompiled_headers_dir = get_precompiled_headers_dir(target_name, subproject_names)
    return None if precompiled_headers_dir is None else os.path.join(precompiled_headers_dir, mangled_file_name + ".h")

def get_precompiled_header_path(target_name, path, subproject_names=None):
    mangled_file_name = mangle_path(path)
    # avoid double .h appearing before .gch
    root, ext = os.path.splitext(mangled_file_name)
    mangled_file_name = root if ext == ".h" else mangled_file_name
    precompiled_headers_dir = get_precompiled_headers_dir(target_name, subproject_names)
    return None if precompiled_headers_dir is None else os.path.join(precompiled_headers_dir, mangled_file_name + ".h.gch")

def get_dependencies_dir(target_name, subproject_names=None):
    target_dir = get_target_dir(target_name, subproject_names)
    return None if target_dir is None else os.path.join(target_dir, "dependencies")
