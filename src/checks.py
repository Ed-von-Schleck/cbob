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
    if target_dir is None:
        return False
    return os.path.isdir(target_dir)

def check_target_exists(target_name):
    if not target_exists(target_name):
        print("ERROR: Target '{}' does not exist.".format(target_name))
        print("Type 'cbob new <target name>' to create a new target,")
        print("'cbob list' to list existing targets or 'cbob --help' for further help.")
        exit(1)
