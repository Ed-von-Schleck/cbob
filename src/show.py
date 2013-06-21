import os

import src.pathhelpers as pathhelpers
import src.checks as checks

@checks.requires_target_exists
def show(target_name):
    sources_dir = pathhelpers.get_sources_dir(target_name)
    print("Sources:")
    for file_name in os.listdir(sources_dir):
        print(" ", file_name)

