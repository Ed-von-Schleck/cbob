import os
import os.path

import cbob.checks as checks
import cbob.pathhelpers as pathhelpers

@checks.requires_initialized
def depend(target_name, dependencies):
    for dep in dependencies:
        checks.check_target_exists(dep)
    dependencies_dir = pathhelpers.get_dependencies_dir(target_name) 
    targets_dir = pathhelpers.get_targets_dir()
    #target_dir = pathhelpers.get_target_dir(target_name)

    for dep in dependencies:
        dep_dir = pathhelpers.get_target_dir(dep)
        dep_symlink = os.path.join(dependencies_dir, dep)
        if os.path.islink(dep_symlink):
            print("Target '{}' is already a dependency of target '{}'.".format(dep, target_name))
            continue
        os.symlink(dep_dir, dep_symlink)

