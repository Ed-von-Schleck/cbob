import glob
import os
import os.path

import cbob.checks as checks
import cbob.pathhelpers as pathhelpers
from cbob.definitions import SOURCE_FILE_EXTENSIONS

@checks.requires_target_exists
def add(target_name, file_names):
    sources_dir = pathhelpers.get_sources_dir(target_name)
    project_root = pathhelpers.get_project_root()
    added_file_names = []
    for file_name in file_names:
        file_name = os.path.expanduser(file_name)
        file_list = glob.glob(file_name)
        if not file_list:
            print("No match for '{}'.".format(file_name))
            continue
        for actual_file_name in file_list:
            #TODO: cleanup
            mangled_file_name = pathhelpers.mangle_path(actual_file_name)
            symlink_path = os.path.join(sources_dir, mangled_file_name)
            if not os.path.splitext(actual_file_name)[1] in SOURCE_FILE_EXTENSIONS:
                print("'{}' does not seem to be a C/C++ source file (ending is not one of {}).".format(actual_file_name, ", ".join(SOURCE_FILE_EXTENSIONS)))
                continue
            if os.path.islink(symlink_path):
                #TODO: only print with some kind of verbosity level
                print("File '{}' is already a source in target '{}'.".format(actual_file_name, target_name))
                continue
            added_file_names.append(actual_file_name)

            abs_actual_file_path = os.path.abspath(actual_file_name)
            rel_actual_path = os.path.normpath(os.path.relpath(abs_actual_file_path, sources_dir))
            os.symlink(rel_actual_path, symlink_path)

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
