import logging
import os
from os.path import normpath, join, isdir, dirname, basename, abspath, islink

from cbob.pathhelpers import read_symlink, expand_glob, make_rel_symlink, print_information

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
            from cbob.target import Target
            targets_dir = join(self.root_path, ".cbob", "targets")
            self._targets = {name: Target(join(targets_dir, name), self) for name in os.listdir(targets_dir) if name is not "_default"}
            if self._targets:
                self._targets["_default"] = self._targets[os.readlink(join(targets_dir, "_default"))]
        return self._targets

    @property
    def subprojects(self):
        if self._subprojects is None:
            subprojects_dir = join(self.root_path, ".cbob", "subprojects")
            self._subprojects = {name: Project(read_symlink(name, subprojects_dir)) for name in os.listdir(subprojects_dir)}
        return self._subprojects

    @property
    def gcc_path(self):
        if self._gcc_path is None:
            try:
                import subprocess
                gcc_path = subprocess.check_output(('which', 'gcc'), universal_newlines=True).strip()
            except subprocess.CalledProcessError as e:
                from cbob.error import CbobError
                raise CbobError("GCC wasn't found ('which gcc' wasn't successful") from e
            self._gcc_path = gcc_path
        return self._gcc_path

    def new_target(self, target_name):
        make_default = "_default" not in self.targets
        assert("." not in target_name) # subprojects should be handled by caller
        if target_name in self.targets:
            from cbob.error import CbobError
            raise CbobError("a target named '{}' already exists".format(target_name))
        new_target_dir = join(self.root_path, ".cbob", "targets", target_name)

        for dir_name in ("sources", "objects", "precompiled_headers", "dependencies"):
            os.makedirs(join(new_target_dir, dir_name))
        if make_default:
            os.symlink(target_name, join(self.root_path, ".cbob", "targets", "_default"))

        self._targets = None
        logging.info("Added new target '{}'".format(target_name))

    def info(self, all_, targets, subprojects):
        if not targets and not subprojects:
            all_ = True
        if all_ or targets:
            if self.targets:
                targets = self.targets
                default_target_name = targets["_default"].name
                del targets["_default"]
                for target_name in targets:
                    print(" ", target_name, "(default)" if target_name == default_target_name else "")
            else:
                print("  (none)")
            print()
        if all_ or subprojects:
            print_information("Subprojects", self.subprojects)

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

    def add_subprojects(self, raw_subproject_paths):
        subprojects_path = join(self.root_path, ".cbob", "subprojects")
        added_subproject_names = []
        for subproject_list in expand_glob(raw_subproject_paths):
            for dir_name, abs_dir_path, symlink_path in self.iter_file_list(subproject_list, subprojects_path):
                if dir_name in self.subprojects:
                    logging.debug("Project '{}' is already a subproject.".format(dir_name))
                    continue
                if not isdir(join(abs_dir_path, ".cbob")):
                    logging.warning("Project '{}' is not really a project (not initialized).".format(dir_name))
                    continue
                added_subproject_names.append(dir_name)
                make_rel_symlink(abs_dir_path, symlink_path)
        added_subprojects_count = len(added_subproject_names)
        if added_subprojects_count == 0:
            logging.warning("No subprojects have been added.")
        elif added_subprojects_count == 1:
            logging.info("Project '{}' has been added as a subproject.".format(added_subproject_names[0]))
        else:
            logging.info("Projects added as subprojects '{}':\n  {}".format(self.name, "\n  ".join(added_subproject_names)))
        self._subprojects = None

    def get_target(self, target_name):
        try:
            return self.targets[target_name]
        except KeyError as e:
            from cbob.error import TargetDoesntExistError
            raise TargetDoesntExistError(target_name) from e

_project = None

def get_project(subproject_names=None):
    global _project
    if _project is None:
        _project = Project()
    current_project = _project
    if subproject_names is not None:
        try:
           while subproject_names:
               subproject_name = subproject_names.pop(0)
               current_project = current_project.subprojects[subproject_name]
        except KeyError as e:
            from cbob.error import SubprojectDoesntExistError
            raise SubprojectDoesntExistError(subproject_name) from e

    return current_project

def init():
    cbob_path = abspath(".cbob") + os.sep
    is_initialized = isdir(".cbob")
    if is_initialized:
        from cbob.error import CbobError
        raise CbobError("cbob is already initialized in '{}'".format(cbob_path))
    os.makedirs(".cbob/targets")
    os.makedirs(".cbob/subprojects")
    logging.info("initialized cbob in '{}'".format(cbob_path))
