import os

import src.pathhelpers as pathhelpers
import src.checks as checks

def show(target_name):
    checks.check_target_exists(target_name)
    sources_dir = pathhelpers.get_sources_dir(target_name)
    print("Sources:")
    for file_name in os.listdir(sources_dir):
        print(" ", file_name)

