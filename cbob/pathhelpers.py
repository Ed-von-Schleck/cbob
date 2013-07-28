import os
from os.path import normpath, join, dirname, relpath

def read_symlink(symlink_name, directory):
    return normpath(join(directory, os.readlink(join(directory, symlink_name))))

def mangle_path(project_root, path):
    abs_actual_file_path = os.path.abspath(path)
    norm_actual_file_path = os.path.normpath(os.path.relpath(abs_actual_file_path, project_root))
    return norm_actual_file_path.replace(os.sep, "_")

def expand_glob(raw_globs):
    import glob
    for raw_glob in raw_globs:
        expanded_glob = glob.glob(os.path.expanduser(raw_glob))
        if not expanded_glob:
            logging.warning("No match for '{}'.".format(raw_glob))
            continue
        yield expanded_glob

def make_rel_symlink(abs_path, symlink_path):
    symlink_dir = dirname(symlink_path)
    rel_path = normpath(relpath(abs_path, symlink_dir))
    return os.symlink(rel_path, symlink_path)

def print_information(name, some_list):
    print(name + ":")
    if some_list:
        for element in some_list:
            print(" ", element)
    else:
        print("  (none)")

