import glob
import os
import os.path

import cbob.checks as checks
import cbob.pathhelpers as pathhelpers

@checks.requires_initialized
def subadd(raw_subproject_paths):
    added_subproject_names = []
    subprojects_dir = pathhelpers.get_subprojects_dir()
    for raw_subproject_path, subproject_paths in expand_glob(raw_subproject_paths):
        for subproject_path in subproject_paths:
            subproject_name = os.path.basename(subproject_path.rstrip(os.sep))
            if checks.subprojects_exist(subproject_name):
                print("There's already a subproject named '{}'.".format(subproject_name))
                continue
            if not checks.is_valid_subproject_path(subproject_path):
                print("'{}' is not a valid path for a subproject (not a subdirectory).".format(subproject_path))
                continue
            symlink_path = os.path.join(subprojects_dir, subproject_name)

            abs_subproject_path = os.path.abspath(subproject_path)
            rel_subproject_path = os.path.normpath(os.path.relpath(abs_subproject_path, subprojects_dir))

            os.symlink(rel_subproject_path, symlink_path)
            added_subproject_names.append(subproject_name)

    added_subprojects_count = len(added_subproject_names)
    if added_subprojects_count == 0:
        print("No subprojects have been added.")
    elif added_subprojects_count == 1:
        print("Subproject '{}' has been added.".format(added_subproject_names[0]))
    else:
        print("Subprojects added:")
        for added_subproject_name in added_subproject_names:
            print(added_subproject_name)
