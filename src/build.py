import locale
import multiprocessing
import os
import os.path
import pickle
import subprocess

import src.pathhelpers as pathhelpers
import src.checks as checks

class _Node(object):
    def __init__(self, file_path, target_name, is_source):
        self.file_path = file_path
        self.last_change = os.path.getmtime(file_path)
        self.depends_on = set()
        self.depended_on_by = set()
        self.is_source = is_source
        if is_source:
            try:
                object_file_path = pathhelpers.get_object_file_path(target_name, file_path)
                self.object_mtime = os.path.getmtime(object_file_path)
            except os.error as e:
                self.object_mtime = 0
        self._sorted = False
        self._being_sorted = False
        self._being_visited = False
        self._visited = False

    def set_depends_on(self, nodes):
        self.depends_on = set(nodes)
        for node in nodes:
            node.depended_on_by.add(self)

    def mark_dirty_recursively(self, node_index, dirty_sources):
        for node in self.depends_on:
            self.last_change = max(node.mark_dirty_recursively(node_index, dirty_sources), self.last_change)
            node.depended_on_by.remove(self)
        self.depends_on.clear()
        if self.file_path in node_index:
            del node_index[self.file_path]
        if self.is_source:
            if self.last_change > self.object_mtime:
                dirty_sources.append(self.file_path)
        return self.last_change

    def clear(self):
        for node in self.depends_on:
            node.depended_on_by.remove(self)
        self.depends_on.clear()
        for node in self.depended_on_by:
            node.depends_on.remove(self)
        self.depended_on_by.clear()


def _compile(cmd):
    print(" ".join(cmd))
    return subprocess.call(cmd)

@checks.requires_configured
def build(target_name, jobs):
    if jobs is not None:
        jobs = jobs[0]
    sources_dir = pathhelpers.get_sources_dir(target_name)
    compiler_path = os.readlink(pathhelpers.get_compiler_symlink(target_name))
    #linker_path = os.readlink(pathhelpers.get_linker_symlink(target_name))
    bindir_path = os.readlink(pathhelpers.get_bindir_symlink(target_name))
    gcc_path = pathhelpers.get_gcc_path()
    deps_file_path = pathhelpers.get_deps_file_path(target_name)
    pool = multiprocessing.Pool(jobs)

    sources = frozenset([pathhelpers.get_source_path_from_symlink(target_name, source) for source in os.listdir(sources_dir)])

    # build graph
    node_index = {}

    make_rules = pool.imap_unordered(subprocess.check_output, ([gcc_path, "-M", file_path] for file_path in sources))
    for make_rule in make_rules:
        make_rule = make_rule.decode(locale.getpreferredencoding())
        object_name, sep, dep_rule = make_rule.partition(":")
        dep_file_paths = [dep for dep in dep_rule.split() if dep != "\\"]

        dep_node_index = {dep: node_index[dep] if dep in node_index else _Node(dep, target_name, dep in sources) for dep in dep_file_paths}
        node_index.update(dep_node_index)

        node = dep_node_index.pop(dep_file_paths[0])
        node.set_depends_on(dep_node_index.values())
    
    dirty_sources = []
    while len(node_index) != 0:
        file_path, node = node_index.popitem()
        node.mark_dirty_recursively(node_index, dirty_sources)

    #TODO: Sort dirty_sources for compile time (longest first).

    if dirty_sources:
        # compile
        cmds = ([compiler_path, "-c", file_path, "-o", pathhelpers.get_object_file_path(target_name, file_path)] for file_path in dirty_sources)
        for result in pool.imap_unordered(_compile, cmds):
            if result != 0:
                exit(result)

        # link
        object_file_names = [pathhelpers.get_object_file_path(target_name, file_path) for file_path in sources]
        cmd = [compiler_path, "-o", os.path.join(bindir_path, target_name)] + object_file_names
        print(" ".join(cmd))
        return_code = subprocess.call(cmd)
        if return_code != 0:
            exit(return_code)
