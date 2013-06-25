import locale
import multiprocessing
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

    def topsort_visit(self, sorted_list, node_set):
        if not self._sorted:
            if self._being_sorted:
                raise CyclicDependencyError(self.file_path)
            self._being_sorted = True
            for node in self.depends_on:
                node.topsort_visit(sorted_list, node_set)
            self._sorted = True
            sorted_list.append(self)
            node_set.discard(self)

    def check_dirty(self, dirty_sources):
        if self.is_source:
            if self.mtime > self.object_mtime:
                dirty_sources.append(self.file_path)

    def update_dependend_on_mtime(self):
        for node in self.depended_on_by:
            node.mtime = max(node.mtime, self.mtime)

def _compile(cmd):
    print(" ".join(cmd))
    ret = subprocess.call(cmd)
    if ret != 0:
        raise CompileError(cmd[2])

@checks.requires_configured
def build(target_name, jobs):
    sources_dir = pathhelpers.get_sources_dir(target_name)
    compiler_path = os.readlink(pathhelpers.get_compiler_symlink(target_name))
    #linker_path = os.readlink(pathhelpers.get_linker_symlink(target_name))
    bindir_path = os.readlink(pathhelpers.get_bindir_symlink(target_name))
    gcc_path = pathhelpers.get_gcc_path()

    sources_set = frozenset([pathhelpers.get_source_path_from_symlink(target_name, source) for source in os.listdir(sources_dir)])

    # build graph
    node_set = set()
    for file_path in sources_set:
        node = _Node(file_path, True)
        node_set.add(node)

        make_rule = subprocess.check_output([gcc_path, "-M", file_path]).decode(locale.getpreferredencoding())
        dep_file_paths = {dep for dep in make_rule.partition(":")[2].split() if dep != "\\"}
        dep_file_paths.remove(file_path)

        dep_node_set = {_Node(dep, dep in sources_set) for dep in dep_file_paths}
        node.set_depends_on(dep_node_set)
        node_set |= dep_node_set
    
    # Sort topologically
    sorted_list = []
    while len(node_set) != 0:
        node = node_set.pop()
        node.topsort_visit(sorted_list, node_set)

    # mark dirty
    dirty_sources = []
    for node in sorted_list:
        node.check_dirty(dirty_sources)
        node.update_dependend_on_mtime()

    #TODO: Sort dirty_sources for compile time (longest first).

    if dirty_sources:
        # compile
        pool = multiprocessing.Pool(jobs)
        cmds = ([compiler_path, "-c", file_path, "-o", pathhelpers.get_object_file_path(file_path)] for file_path in dirty_sources)
        try:
            pool.map(_compile, cmds)
        except CompileError as e:
            print(e)
            exit(1)
        pool.close()
        pool.join()

        # link
        object_file_names = [pathhelpers.get_object_file_path(file_path) for file_path in sources_set]
        cmd = [compiler_path, "-o", os.path.join(bindir_path, target_name)] + object_file_names
        print(" ".join(cmd))
        return_code = subprocess.call(cmd)
        if return_code != 0:
            exit(return_code)

class CyclicDependencyError(Exception):
    def __init__(self, file_path):
        self.file_path = file_path
    def __str__(self):
        return "ERROR: Detected cyclic include dependency in file '{}'.".format(self.file_path)

class CompileError(Exception):
    def __init__(self, file_path):
        self.file_path = file_path
    def __str__(self):
        return "ERROR: Compilation of file '{}' failed.".format(self.file_path)
