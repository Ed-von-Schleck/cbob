import os

import src.pathhelpers as pathhelpers

def list_():
    targets_dir = pathhelpers.get_targets_dir()
    for target_name in os.listdir(targets_dir):
        print(target_name)
