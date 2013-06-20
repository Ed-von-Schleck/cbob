import glob
import os
import os.path

import src.checks as checks
import src.pathhelpers as pathhelpers

@checks.requires_initialized
def add(target_name, file_names):
    checks.check_target_exists(target_name)
    sources_dir = pathhelpers.get_sources_dir(target_name)
    project_root = pathhelpers.get_project_root()
    added_file_names = []
    for file_name in file_names:
        file_name = os.path.expanduser(file_name)
        file_list = glob.glob(file_name)
        if not file_list:
            print("WARNING: No match for '{}'.".format(file_name))
            continue
        for actual_file_name in file_list:
            abs_actual_file_name = os.path.abspath(actual_file_name)
            rel_actual_file_name = os.path.normpath(os.path.relpath(abs_actual_file_name, project_root))
            mangled_file_name = rel_actual_file_name.replace(os.sep, "_")
            symlink_path = os.path.join(sources_dir, mangled_file_name)
            if os.path.islink(symlink_path):
                #TODO: only print with some kind of verbosity level
                print("File '{}' is already a source in target '{}'.".format(actual_file_name, target_name))
                continue
            added_file_names.append(actual_file_name)
            os.symlink(actual_file_name, os.path.join(sources_dir, mangled_file_name))

    added_files_count = len(added_file_names)
    #TODO: only print with some kind of verbosity level
    if added_files_count == 0:
        print("No files have been added to target '{}'.".format(target_name))
    elif added_files_count == 1:
        print("File '{}' has been added to target '{}'.".format(added_file_names[0], target_name))
    else:
        print("Files added to target '{}':".format(target_name))
        for added_file_name in added_file_names:
            print(added_file_name)
