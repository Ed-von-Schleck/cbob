import logging
import os
from os.path import normpath, join, isdir, dirname, basename, abspath, islink, commonprefix, relpath, expanduser

from cbob.helpers import read_symlink, make_rel_symlink, print_information, log_summary
from cbob.paths import DirNamespace
from cbob.lazyattribute import lazy_attribute

class Project(object):
    def __init__(self, root_path=None):
        if root_path is None:
            path = os.getcwd()
            oldpath = ""
            while path != oldpath:
                if isdir(join(path, ".cbob")):
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
        self.dirs = DirNamespace(join(self.root_path, ".cbob"), {
            "subprojects": "subprojects",
            "targets": "targets"})

    @lazy_attribute
    def targets(self):
        from cbob.target import Target
        targets_dir = self.dirs.targets
        targets = {name: Target(join(targets_dir, name), self) for name in os.listdir(targets_dir) if name is not "_default"}
        if targets:
            targets["_default"] = targets[os.readlink(join(targets_dir, "_default"))]
        return targets

    @lazy_attribute
    def subprojects(self):
        subprojects_dir = self.dirs.subprojects
        return {name: Project(read_symlink(name, subprojects_dir)) for name in os.listdir(subprojects_dir)}

    @lazy_attribute
    def gcc_path(self):
        try:
            import subprocess
            gcc_path = subprocess.check_output(('which', 'gcc'), universal_newlines=True).strip()
        except subprocess.CalledProcessError as e:
            from cbob.error import CbobError
            raise CbobError("GCC wasn't found ('which gcc' wasn't successful") from e
        return gcc_path

    def new_target(self, target_name):
        make_default = not islink(join(self.dirs.targets, "_default"))
        assert("." not in target_name) # subprojects should be handled by caller
        new_target_dir = join(self.dirs.targets, target_name)
        if isdir(new_target_dir):
            from cbob.error import CbobError
            raise CbobError("a target named '{}' already exists".format(target_name))
        os.makedirs(new_target_dir)

        if make_default:
            os.symlink(target_name, join(self.dirs.targets, "_default"))

        self.targets = None
        logging.info("Added new target '{}'".format(target_name))

    def delete_target(self, target_name):
        is_default = os.readlink(join(self.dirs.targets, "_default")) == target_name
        target_dir = join(self.dirs.targets, target_name)
        import shutil
        try:
            shutil.rmtree(target_dir)
        except OSError as e:
            from cbob.error import TargetDoesntExistError
            raise TargetDoesntExistError(target_name) from e
        if is_default:
            os.unlink(join(self.dirs.targets, "_default"))
            logging.info("Unset target '{}' as default target".format(target_name))
        logging.info("Removed target '{}'".format(target_name))

    def info(self, all_, targets, subprojects):
        if not targets and not subprojects:
            all_ = True
        if all_ or targets:
            print()
            print("Targets:")
            if self.targets:
                default_target_name = self.targets["_default"].name
                for target_name in self.targets:
                    if target_name != "_default":
                        print(" ", target_name, "(default)" if target_name == default_target_name else "")
            else:
                print("  (none)")
        if all_ or subprojects:
            print()
            print_information("Subprojects", self.subprojects)

    def mangle_path(self, path):
        return normpath(relpath(abspath(path), self.root_path)).replace(os.sep, "_")

    def _iter_globs(self, globs, directory):
        import glob
        for raw_glob in globs:
            file_list = glob.glob(expanduser(raw_glob))
            if not file_list:
                logging.warning("No match for '{}'.".format(raw_glob))
                continue
            for file_name in file_list:
                symlink_path = join(directory, self.mangle_path(file_name))
                abs_file_path = abspath(file_name)
                yield (file_name, abs_file_path, symlink_path)

    def _subproject_check(self, dir_name, abs_dir_path, symlink_path):
        if not isdir(join(abs_dir_path, ".cbob")):
            logging.warning("Project '{}' is not really a project (not initialized).".format(dir_name))
            return False
        return True

    def subprojects_add(self, subproject_globs):
        self._add_something_from_globs(self.dirs.subprojects, subproject_globs, "subproject", [self._subproject_check])
        self.subprojects = None

    def subprojects_remove(self, subproject_globs):
        self._remove_something_from_globs(self.dirs.subprojects, subproject_globs, "subproject")
        self.subprojects = None

    def get_target(self, target_name=None):
        if target_name is None:
            target_name = "_default"
        try:
            return self.targets[target_name]
        except KeyError as e:
            from cbob.error import TargetDoesntExistError
            raise TargetDoesntExistError(target_name) from e

    def _add_something_from_globs(self, dir_path, globs, thing, checks=None, target_name=None):
        added_things = []
        for file_name, abs_file_path, symlink_path in self._iter_globs(globs, dir_path):
            if islink(symlink_path):
                tail = " of target '{}'".format(target_name) if target_name is not None else ""
                logging.debug("'{}' is already a {}{}.".format(file_name, thing, tail))
                continue
            if commonprefix((abs_file_path, self.root_path)) != self.root_path:
                logging.warning("{} '{}' is not in a (sub)-direcory of the project.".format(thing.capitalize(), file_name))
                continue
            if checks is not None:
                fail = False
                for check in checks:
                    if not check(file_name, abs_file_path, symlink_path):
                        fail = True
                        break
                if fail:
                    continue
            added_things.append(file_name)
            make_rel_symlink(abs_file_path, symlink_path)
        log_summary(added_things, thing, added=True, target_name=target_name)
        

    def _remove_something_from_globs(self, dir_path, globs, thing, target_name=None):
        removed_things = []
        for file_name, abs_file_path, symlink_path in self._iter_globs(globs, dir_path):
            try:
                os.unlink(symlink_path)
            except OSError:
                tail = " of target '{}'".format(target_name) if target_name is not None else ""
                logging.debug("{}' is not a {}{}.".format(file_name, thing, tail))
                continue
            removed_things.append(file_name)
        log_summary(removed_things, thing, added=False, target_name=target_name)

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
