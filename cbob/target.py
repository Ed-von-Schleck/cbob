import logging
import os
from os.path import basename, join, islink

from cbob.pathhelpers import read_symlink, mangle_path, expand_glob
from cbob.definitions import SOURCE_FILE_EXTENSIONS

class Target(object):
    __slots__ = ("path", "name", "_sources", "project")

    def __init__(self, path, project):
        self.path = path
        self.name = basename(path)
        self.project = project
        self._sources = None

    @property
    def sources(self):
        if self._sources is None:
            sources_dir = join(self.path, "sources")
            self._sources = [read_symlink(name, sources_dir) for name in os.listdir(ources_dir)]
        return self._sources

    def add_sources(self, source_globs):
        sources_dir = join(self.path, "sources")
        added_file_names = []
        for source_glob, file_list in expand_glob(source_globs):
            for file_name, rel_file_path, symlink_path in self.project.iter_file_list(file_list, sources_dir):
                if not os.path.splitext(file_name)[1] in SOURCE_FILE_EXTENSIONS:
                    logging.warning("'{}' does not seem to be a C/C++ source file (ending is not one of {}).".format(file_name, ", ".join(SOURCE_FILE_EXTENSIONS)))
                    continue
                if islink(symlink_path):
                    logging.debug("File '{}' is already a source file of target '{}'.".format(file_name, self.name))
                    continue
                added_file_names.append(file_name)
                os.symlink(rel_file_path, symlink_path)

        added_files_count = len(added_file_names)
        if added_files_count == 0:
            logging.info("No files have been added to target '{}'.".format(self.name))
        elif added_files_count == 1:
            logging.info("File '{}' has been added to target '{}'.".format(added_file_names[0], self.name))
        else:
            logging.info("Files added to target '{}':\n  {}".format(self.name, "\n  ".join(added_file_names)))
        self._sources = None
    
    def remove_sources(self, source_globs):
        sources_dir = join(self.path, "sources")
        removed_file_names = []
        for source_glob, file_list in expand_glob(source_globs):
            for file_name, rel_file_path, symlink_path in self.project.iter_file_list(file_list, sources_dir):
                try:
                    os.unlink(symlink_path)
                except OSError:
                    logging.debug("File '{}' not a source file of target '{}'.".format(file_name, self.name))
                    continue
                removed_file_names.append(file_name)

        removed_files_count = len(removed_file_names)
        if removed_files_count == 0:
            logging.info("No files have been removed from to target '{}'.".format(self.name))
        elif removed_files_count == 1:
            logging.info("File '{}' has been removed from target '{}'.".format(removed_file_names[0], self.name))
        else:
            logging.info("Files removed from target '{}':\n  {}".format(self.name, "\n  ".join(added_file_names)))
        self._sources = None


    def show_sources(self):
        for file_name in self.sources:
            print(file_name)
