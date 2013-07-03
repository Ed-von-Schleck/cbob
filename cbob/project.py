import logging
import os
from os.path import normpath, join, isdir, dirname, basename, abspath

from cbob.target import Target
from cbob.pathhelpers import read_symlink

class Project(object):

    def __init__(self, root_path=None):
        if root_path is None:
            path = os.getcwd()
            oldpath = ""
            while path != oldpath:
                if isdir(os.path.join(path, ".cbob")):
                    self.root_path = path
                    break
                oldpath = path
                path = dirname(path)
            else:
                from cbob.error import NotInitializedError
                raise NotInitializedError()
        else:
            self.root_path = root_path

        self.name = basename(self.root_path)
        self._subprojects = None
        self._targets = None
        self._gcc_path = None

    @property
    def targets(self):
        if self._targets is None:
            targets_dir = join(self.root_path, ".cbob", "targets")
            self._targets = {name: Target(join(targets_dir, name), self) for name in os.listdir(targets_dir)}
        return self._targets

    @property
    def subprojects(self):
        if self._subprojects is None:
            subprojects_dir = join(self.root_path, ".cbob", "subprojects")
            self.subprojects = {name: Project(read_symlink(name, subprojects_dir)) for name in os.listdir(subprojects_dir)}
        return self._subprojects

    @property
    def gcc_path(self):
        if self._gcc_path is None:
            import subprocess
            try:
                gcc_path = subprocess.check_output(('which', 'gcc'), universal_newlines=True).strip()
            except subprocess.CalledProcessError as e:
                from cbob.error import CbobError
                raise CbobError("GCC wasn't found ('which gcc' wasn't successful")
            self._gcc_path = gcc_path
        return self._gcc_path

    def new_target(self, raw_target_name):
        *subproject_names, target_name = raw_target_name.split(".")
        logging.debug("subprojects: " + str(subproject_names))
        if subproject_names:
            from cbob.error import CbobError
            raise CbobError("subprojects are not yet fully supported")
        if target_name in self.targets:
            from cbob.error import CbobError
            raise CbobError("a target named '{}' already exists".format(target_name))
        new_target_dir = join(self.root_path, ".cbob", "targets", target_name)
        os.makedirs(os.path.join(new_target_dir, "sources"))
        os.makedirs(os.path.join(new_target_dir, "objects"))
        os.makedirs(os.path.join(new_target_dir, "precompiled_headers"))
        os.makedirs(os.path.join(new_target_dir, "dependencies"))
        self._targets = None
        logging.info("Added new target '{}'".format(target_name))

    def list_targets(self):
        for target_name in self.targets:
            print(target_name)

    def mangle_path(self, path):
        abs_actual_file_path = os.path.abspath(path)
        norm_actual_file_path = os.path.normpath(os.path.relpath(abs_actual_file_path, self.root_path))
        return norm_actual_file_path.replace(os.sep, "_")

    def iter_file_list(self, file_list, directory):
        for file_name in file_list:
            mangled_file_name = self.mangle_path(file_name)
            symlink_path = join(directory, mangled_file_name)

            abs_file_path = os.path.abspath(file_name)
            yield (file_name, abs_file_path, symlink_path)

_project = None

def get_project():
    global _project
    if _project is None:
        _project = Project()
    return _project

def init():
    cbob_path = abspath(".cbob") + os.sep
    is_initialized = isdir(".cbob")
    if is_initialized:
        from cbob.error import CbobError
        raise CbobError("cbob is already initialized in '{}'".format(cbob_path))
    os.makedirs(".cbob/targets")
    os.makedirs(".cbob/subprojects")
    logging.info("initialized cbob in '{}'".format(cbob_path))
