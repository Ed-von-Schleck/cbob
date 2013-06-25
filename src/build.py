import locale
import os
import os.path
import subprocess

import src.pathhelpers as pathhelpers
import src.checks as checks

class _Node(object):
    def __init__(self, file_path, is_source):
        self.file_path = file_path
        self.mtime = os.path.getmtime(file_path)
        self.depends_on = set()
        self.depended_on_by = set()
        self.is_source = is_source
        if is_source:
            try:
                object_file_path = pathhelpers.get_object_file_path(file_path)
                self.object_mtime = os.path.getmtime(object_file_path)
            except os.error as e:
                self.object_mtime = 0
        self._sorted = False
        self._being_sorted = False

    def set_depends_on(self, nodes):
        self.depends_on = set(nodes)
        for node in nodes:
            node.depended_on_by.add(self)

    def topsort_visit(self, sorted_list):
        if not self._sorted:
            if self._being_sorted:
                raise CyclicDependencyError(self.file_path)
            self._being_sorted = True
            for node in self.depends_on:
                if node is not self:
                    node.topsort_visit(sorted_list)
            self._sorted = True
            sorted_list.append(self)

    def check_dirty(self, dirty_sources):
        if self.is_source:
            if self.mtime > self.object_mtime:
                dirty_sources.append(self.file_path)

    def update_dependend_on_mtime(self):
        for node in self.depended_on_by:
            node.mtime = max(node.mtime, self.mtime)


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

    real_sources_path_list = frozenset([pathhelpers.get_source_path_from_symlink(target_name, source) for source in os.listdir(sources_dir)])

    # build graph
    node_index = {}
    for file_path in real_sources_path_list:
        make_rule = subprocess.check_output([gcc_path, "-M", file_path]).decode(locale.getpreferredencoding())
        dep_file_paths = [dep for dep in make_rule.partition(":")[2].split() if dep != "\\"]

        # add all dependencies of that file to the graph
        # (note that the file is always a dependency of itself, no need to add it explicitly)
        for dep in dep_file_paths:
            if not dep in node_index:
                node_index[dep] = _Node(dep, dep in real_sources_path_list)

        dep_nodes = {node_index[dep] for dep in dep_file_paths}
        node_index[file_path].set_depends_on(dep_nodes)
    
    # Sort topologically
    sorted_list = []
    for node in node_index.values():
        node.topsort_visit(sorted_list)

    dirty_sources = []
    for node in sorted_list:
        node.check_dirty(dirty_sources)
        node.update_dependend_on_mtime()

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

class CyclicDependencyError(Exception):
    def __init__(self, file_path):
        self.file_path = file_path
    def __str__(self):
        return "Detected cyclic include dependency in file '{}'.".format(self.file_path)
