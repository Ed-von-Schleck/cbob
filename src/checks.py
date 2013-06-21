import functools
import os.path

import src.pathhelpers as pathhelpers

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

def target_exists(target_name):
    target_dir = pathhelpers.get_target_dir(target_name)
    return target_dir is not None and os.path.isdir(target_dir)

@requires_initialized
def requires_target_exists(func):
    """first parameter must be 'target_name'"""
    @functools.wraps(func)
    def wrapper(target_name, *args, **kwargs):
        if not target_exists(target_name):
            print("ERROR: Target '{}' does not exist.".format(target_name))
            print("Type 'cbob new <target name>' to create a new target,")
            print("'cbob list' to list existing targets or 'cbob --help' for further help.")
            exit(1)
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
            print("ERROR: No compiler configured (use 'cbob configure --compiler=\"<path-to-compiler>\"' or 'cbob configure --auto')")
            exit(1)
        if not is_linker_configured(target_name):
            print("ERROR: No linker configured (use 'cbob configure --compiler=\"<path-to-linker>\"' or 'cbob configure --auto')")
            exit(1)

        return func(target_name, *args, **kwargs)
    return wrapper

