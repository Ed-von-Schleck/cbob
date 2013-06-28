import functools
import multiprocessing
import os
import os.path
#import pickle
import subprocess
import sys

import src.pathhelpers as pathhelpers
import src.checks as checks

class _Node(object):
    __slots__ = ("file_path", "target_name", "is_source", "depends_on")

    def __init__(self, file_path, target_name, is_source):
        self.file_path = file_path
        self.target_name = target_name
        self.is_source = is_source
        self.depends_on = set()

    def mark_dirty_recursively(self, dirty_sources, object_mtime=None):
        last_change = os.path.getmtime(self.file_path)

        if object_mtime is None:
            try:
                object_file_path = pathhelpers.get_object_file_path(self.target_name, self.file_path)
                object_mtime = os.path.getmtime(object_file_path)
            except OSError:
                self.depends_on.clear()
                dirty_sources.append(self.file_path)
                return last_change

        while last_change <= object_mtime and self.depends_on:
            node = self.depends_on.pop()
            last_change = max(node.mark_dirty_recursively(dirty_sources, object_mtime), last_change)
                
        if self.is_source and last_change > object_mtime:
            dirty_sources.append(self.file_path)

        return last_change

    def clear(self):
        self.depends_on.clear()


def _compile(cmd):
    print(" ".join(cmd))
    return subprocess.call(cmd)

def _compile_source(file_path, compiler_path, target_name):
    print(" ", file_path)
    cmd = [compiler_path, "-c", file_path, "-o", pathhelpers.get_object_file_path(target_name, file_path)]
    return subprocess.call(cmd)

def _get_dep_info(file_path):
    cmd = [pathhelpers.get_gcc_path(), "-H", "-w", "-E", "-P", file_path]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
        out, err = process.communicate()
    raw_deps = (line.partition(" ") for line in err.split("\n") if line and line[0] == ".")
    deps = [(len(dots), os.path.normpath(rest)) for (dots, sep, rest) in raw_deps]
    return file_path, deps

@checks.requires_configured
def build(target_name, jobs):
    if jobs is not None:
        jobs = jobs[0]
    sources_dir = pathhelpers.get_sources_dir(target_name)
    compiler_path = os.readlink(pathhelpers.get_compiler_symlink(target_name))
    #linker_path = os.readlink(pathhelpers.get_linker_symlink(target_name))
    gcc_path = pathhelpers.get_gcc_path()
    deps_file_path = pathhelpers.get_deps_file_path(target_name)
    pool = multiprocessing.Pool(jobs)

    print("calculating dependencies ...", end=" ")
    sys.stdout.flush()
    sources = [pathhelpers.get_source_path_from_symlink(target_name, source) for source in os.listdir(sources_dir)]
    source_node_index = {file_path: _Node(file_path, target_name, True) for file_path in sources}
    
    # build graph
    node_index = source_node_index.copy()

    #try:
    #    with open(deps_file_path, "rb") as deps_file:
    #        stale_node_index = pickle.load(deps_file)
    #except (IOError, pickle.UnpicklingError):
    #    stale_node_index = {}
    #new_source_nodes = sources - stale_node_index.keys()

    
    processed_nodes = set()
    for file_path, deps in pool.imap_unordered(_get_dep_info, sources):
        parent_nodes_stack = [source_node_index[file_path]]

        for current_depth, dep_path in deps:
            if dep_path in node_index:
                current_node = node_index[dep_path]
                if current_node in processed_nodes:
                    continue
                processed_nodes |= current_node.depends_on
            else:
                current_node = _Node(dep_path, target_name, dep_path in source_node_index)
                node_index[dep_path] = current_node

            parent_nodes_stack[:] = parent_nodes_stack[:current_depth]
            parent_nodes_stack[-1].depends_on.add(current_node)
            parent_nodes_stack.append(current_node)


    #with open(deps_file_path, "wb") as deps_file:
    #    pickle.dump(node_index, deps_file, -1)
    print("done.")

    print("determining files for recompilation ...", end=" ")
    sys.stdout.flush()
    dirty_sources = []
    for source_node in source_node_index.values():
        source_node.mark_dirty_recursively(dirty_sources)
    print("done.")

    #TODO: Sort dirty_sources for compile time (longest first).

    if dirty_sources:
        # compile
        compile_func = functools.partial(_compile_source, compiler_path=compiler_path, target_name=target_name)
        #cmds = ([compiler_path, "-c", file_path, "-o", pathhelpers.get_object_file_path(target_name, file_path)] for file_path in dirty_sources)
        print("compiling ...")
        sys.stdout.flush()
        for result in pool.imap_unordered(compile_func, dirty_sources):
            if result != 0:
                exit(result)
        print("done.")

        # link
        object_file_names = [pathhelpers.get_object_file_path(target_name, file_path) for file_path in sources]
        bin_path = pathhelpers.get_bin_path(target_name)
        cmd = [compiler_path, "-o", bin_path] + object_file_names
        print("linking ...")
        print(" ", bin_path)
        sys.stdout.flush()
        return_code = subprocess.call(cmd)
        if return_code != 0:
            exit(return_code)
        print("done.")
    else:
        print("Nothing to do.")
