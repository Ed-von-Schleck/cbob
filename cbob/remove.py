import glob
import os
import os.path

import cbob.checks as checks
import cbob.pathhelpers as pathhelpers

@checks.requires_target_exists
def remove(target_name, file_names):
    #TODO: remove code duplication with 'add.py'
    sources_dir = pathhelpers.get_sources_dir(target_name)
    removed_file_names = []
    for file_name in file_names:
        file_name = os.path.expanduser(file_name)
        file_list = glob.glob(file_name)
        if not file_list:
            print("No match for '{}'.".format(file_name))
            continue
        for actual_file_name in file_list:
            mangled_file_name = pathhelpers.mangle_path(actual_file_name)
            symlink_path = os.path.join(sources_dir, mangled_file_name)
            try:
                os.unlink(symlink_path)
            except OSError:
                print("File '{}' not a source file of target '{}'.".format(actual_file_name, target_name))
                continue
            removed_file_names.append(actual_file_name)

    removed_files_count = len(removed_file_names)
    if removed_files_count == 0:
        print("No files have been removed from to target '{}'.".format(target_name))
    elif removed_files_count == 1:
        print("File '{}' has been removed from target '{}'.".format(removed_file_names[0], target_name))
    else:
        print("Files removed from target '{}':".format(target_name))
        for removed_file_name in removed_file_names:
            print(removed_file_name)


