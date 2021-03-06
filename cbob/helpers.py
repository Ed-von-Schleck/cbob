import logging
import os
from os.path import normpath, join, dirname, relpath

def read_symlink(symlink_name, directory):
    return normpath(join(directory, os.readlink(join(directory, symlink_name))))

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

def log_summary(changed_items, thing, added, target_name=None, plural=None):
    changed_items_count = len(changed_items)
    added_or_removed = "added" if added else "removed"
    to_or_from = "to" if added else "from"
    tail = " {} target '{}'".format(to_or_from, target_name) if target_name is not None else ""
    if plural is None:
        plural = "{}s".format(thing)
    if changed_items_count == 0:
        logging.warning("No {}s have been {}{}.".format(thing, added_or_removed, tail))
    elif changed_items_count == 1:
        logging.info("{} '{}' has been {}{}.".format(thing.capitalize(), changed_items[0], added_or_removed, tail))
    else:
        logging.info("{}s {}{}:\n  {}".format(thing.capitalize(), added_or_removed, tail, "\n  ".join(changed_items)))

