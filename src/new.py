import os

import src.checks as checks
import src.pathhelpers as pathhelpers

@checks.requires_initialized
def new(target_name):
    target_name = target_name.lower()
    if checks.target_exists(target_name):
        print("ERROR: A Target named '{}' already exists. Please choose another name.".format(target_name))
        exit(1)
    new_target_dir = pathhelpers.get_target_dir(target_name)
    os.makedirs(os.path.join(new_target_dir, "sources"))
    print("Added new target '{}'".format(target_name))
