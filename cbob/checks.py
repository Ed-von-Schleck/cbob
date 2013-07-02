import functools
import os.path

import cbob.pathhelpers as pathhelpers

def is_initialized_recursive():
    return pathhelpers.get_project_root() is not None

def requires_initialized(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not is_initialized_recursive():
            print("ERROR: cbob is not initialized.")
            print("Type 'cbob init' in your projects root directory to initialize cbob")
            print("or 'cbob --help' for further help.")
            exit(1)
        return func(*args, **kwargs)
    return wrapper

def target_exists(target_name, subproject_names=None):
    target_dir = pathhelpers.get_target_dir(target_name, subproject_names)
    return target_dir is not None and os.path.isdir(target_dir)

def check_target_exists(target_name):
    if not target_exists(target_name):
        print("ERROR: Target '{}' does not exist.".format(target_name))
        print("Type 'cbob new <target name>' to create a new target,")
        print("'cbob list' to list existing targets or 'cbob --help' for further help.")
        exit(1)

@requires_initialized
def requires_target_exists(func):
    """first parameter must be 'target_name'"""
    @functools.wraps(func)
    def wrapper(target_name, *args, **kwargs):
        check_target_exists(target_name)
        return func(target_name, *args, **kwargs)
    return wrapper

def is_compiler_configured(target_name):
    return os.path.islink(pathhelpers.get_compiler_symlink(target_name))

def is_linker_configured(target_name):
    return os.path.islink(pathhelpers.get_linker_symlink(target_name))

def requires_configured(func):
    """first parameter must be 'target_name'"""
    @functools.wraps(func)
    @requires_initialized
    @requires_target_exists
    def wrapper(target_name, *args, **kwargs):
        if not is_compiler_configured(target_name):
            print("ERROR: No compiler configured (use 'cbob configure --compiler=\"<path-to-compiler>\" {0}' or 'cbob configure --auto {0}').".format(target_name))
            exit(1)
        if not is_linker_configured(target_name):
            print("ERROR: No linker configured (use 'cbob configure --compiler=\"<path-to-linker>\" {0}' or 'cbob configure --auto {0}').".format(target_name))
            exit(1)

        return func(target_name, *args, **kwargs)
    return wrapper

def subprojects_exist(subproject_names):
    return pathhelpers.get_subproject_root(subproject_names) is not None

def check_subprojects_exist(subproject_names):
    if not subprojects_exist(subproject_names):
        print("ERROR: Subproject '{}' does not exist.".format(".".join(subproject_names)))
        exit(1)

def is_valid_subproject_path(subproject_path, subproject_names=None):
    # checks if path is a subpath of the super-project,
    # not if the path is a valid path itself
    abs_subproject_path = os.path.abspath(subproject_path)
    project_root = pathhelpers.get_project_root() if subproject_names is None else pathhelpers.get_subproject_root(subproject_names)
    return os.path.commonprefix((abs_subproject_path, project_root)) == project_root
