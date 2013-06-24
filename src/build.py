import locale
import os
import os.path
import subprocess

import src.pathhelpers as pathhelpers
import src.checks as checks

class _Node(object):
    def __init__(self, file_path):
        self.file_path = file_path
        self.depends_on = set()
        self.depended_on_by = set()

    def set_depends_on(self, nodes):
        self.depends_on = set(nodes)
        for node in nodes:
            node.depended_on_by.add(self)

    def write_dirty_recursively(self, dirty_sources):
        if self.file_path not in dirty_sources:
            for node in self.depended_on_by:
                if node is not self:
                    node.write_dirty_recursively(dirty_sources)
            dirty_sources.add(self.file_path)

    def check_dependencys_recursively(self, object_mtime, dirty_sources):
        mtime = os.path.getmtime(self.file_path)
        if mtime > object_mtime:
            self.write_dirty_recursively(dirty_sources)
            return True
        else:
            for dep in self.depends_on:
                if dep is not self:
                    done = dep.check_dependencys_recursively(object_mtime, dirty_sources)
                    if done:
                        return True
            return False

    def clear_depends_on(self):
        for node in self.depends_on:
            node.depended_on_by.remove(self)
        self.depends_on.clear()

@checks.requires_configured
def build(target_name):
    sources_dir = pathhelpers.get_sources_dir(target_name)
    compiler_path = os.readlink(pathhelpers.get_compiler_symlink(target_name))
    #linker_path = os.readlink(pathhelpers.get_linker_symlink(target_name))
    bindir_path = os.readlink(pathhelpers.get_bindir_symlink(target_name))
    gcc_path = pathhelpers.get_gcc_path()

    real_sources_path_list = [pathhelpers.get_source_path_from_symlink(target_name, source) for source in os.listdir(sources_dir)]

    # build graph
    node_index = {}
    for file_path in real_sources_path_list:
        make_rule = subprocess.check_output([gcc_path, "-M", file_path]).decode(locale.getpreferredencoding())
        dep_file_paths = [dep for dep in make_rule.partition(":")[2].split() if dep != "\\"]

        # add all dependencies of that file to the graph
        # (note that the file is always a dependency of itself, no need to add it explicitly)
        for dep in dep_file_paths:
            if not dep in node_index:
                node_index[dep] = _Node(dep)

        dep_nodes = {node_index[dep] for dep in dep_file_paths}
        node_index[file_path].set_depends_on(dep_nodes)

    # check for files in need of recompilation
    dirty_sources = set()
    for file_path in real_sources_path_list:
        if file_path in dirty_sources:
            continue # already marked for recompilation
        node = node_index[file_path]
        try:
            object_file_path = pathhelpers.get_object_file_path(file_path)
            object_mtime = os.path.getmtime(object_file_path)
        except os.error as e:
            node.write_dirty_recursively(dirty_sources)
            continue
        # checking only the file_path's mtime is not enough; there are dependencies that are not
        # sources (like headers) and don't correspond to an object file - these wouldn't be checked
        node.check_dependencys_recursively(object_mtime, dirty_sources)

    # compile
    for file_path in dirty_sources: 
        object_file_path = pathhelpers.get_object_file_path(file_path)

        cmd = [compiler_path, "-c", file_path, "-o", object_file_path]
        print(" ".join(cmd))
        return_code = subprocess.call(cmd)
        if return_code != 0:
            exit(return_code)

    # link
    if dirty_sources:
        object_file_names = [pathhelpers.get_object_file_path(file_path) for file_path in real_sources_path_list]
        cmd = [compiler_path, "-o", os.path.join(bindir_path, target_name)] + object_file_names
        print(" ".join(cmd))
        return_code = subprocess.call(cmd)
        if return_code != 0:
            exit(return_code)
