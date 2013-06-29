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
    __slots__ = ("file_path", "target_name", "dependencies", "last_dep_change")

    def __init__(self, file_path, target_name):
        self.file_path = file_path
        self.target_name = target_name
        self.dependencies = set()
        self.last_dep_change = None

    def mark_dirty_recursively(self, dirty_sources, dirty_headers, object_mtime=None, depth=0):
        is_source = object_mtime is None
        if is_source:
            # We need to check the headers even if the source is dirty, because we might need to
            # re-precompile the headers too.
            object_file_path = pathhelpers.get_object_file_path(self.target_name, self.file_path)
            object_mtime = os.path.getmtime(object_file_path) if os.path.isfile(object_file_path) else 0

            precompiled_header_path = pathhelpers.get_precompiled_header_path(self.target_name, self.file_path)
            precompiled_header_mtime = os.path.getmtime(precompiled_header_path) if os.path.isfile(precompiled_header_path) else -1

        self.last_dep_change = 0 if is_source else self.last_dep_change if self.last_dep_change is not None else os.path.getmtime(self.file_path)

        while self.dependencies and self.last_dep_change <= object_mtime:
            node = self.dependencies.pop()
            node_last_dep_change = node.mark_dirty_recursively(dirty_sources, dirty_headers, object_mtime, depth + 1)
            self.last_dep_change = max(node_last_dep_change, self.last_dep_change)
                
        if is_source:
            last_change = max(self.last_dep_change, os.path.getmtime(self.file_path))
            if last_change > object_mtime:
                dirty_sources.add(self.file_path)
                if self.last_dep_change > precompiled_header_mtime:
                    uncompiled_header_path = pathhelpers.get_uncompiled_header_path(self.target_name, self.file_path)
                    dirty_headers.add(uncompiled_header_path)
            self.last_dep_change = last_change

        return self.last_dep_change

    def clear(self):
        self.dependencies.clear()


def _compile(file_path, compiler_path, target_name, c_switch=False, get_output_path=None, include_pch=False):
    print(" ", file_path)
    cmd = [compiler_path, file_path]
    if get_output_path is not None:
        cmd += ["-o", get_output_path(target_name, file_path)]
    if c_switch:
        cmd.append("-c")
    if include_pch:
        cmd += ["-fpch-preprocess", "-include", pathhelpers.get_uncompiled_header_path(target_name, file_path)]

    process = subprocess.Popen(cmd)
    #print(" ".join(cmd))
    return process.wait()

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
    source_node_index = {file_path: _Node(file_path, target_name) for file_path in sources}
    
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
        node = source_node_index[file_path]
        parent_nodes_stack = [node]

        includes = set()

        for current_depth, dep_path in deps:
            includes.add("#include \"" + dep_path + "\"\n")
            if dep_path in node_index:
                current_node = node_index[dep_path]
                if current_node in processed_nodes:
                    continue
                processed_nodes |= current_node.dependencies
            else:
                current_node = _Node(dep_path, target_name)
                node_index[dep_path] = current_node

            parent_nodes_stack[:] = parent_nodes_stack[:current_depth]
            parent_nodes_stack[-1].dependencies.add(current_node)
            parent_nodes_stack.append(current_node)

        uncompiled_header_path = pathhelpers.get_uncompiled_header_path(target_name, file_path)
        changed = False
        try:
            with open(uncompiled_header_path, "r") as uncompiled_header:
                if includes.symmetric_difference(uncompiled_header):
                    changed = True
        except IOError:
            changed = True
        if changed:
            with open(uncompiled_header_path, "w") as uncompiled_header:
                uncompiled_header.writelines(includes)
                
            precompiled_header_path = pathhelpers.get_precompiled_header_path(target_name, file_path)
            try:
                os.remove(precompiled_header_path)
            except OSError:
                pass


    #with open(deps_file_path, "wb") as deps_file:
    #    pickle.dump(node_index, deps_file, -1)
    print("done.")

    print("determining files for recompilation ...", end=" ")
    sys.stdout.flush()

    dirty_sources = set()
    dirty_headers = set()
    for source_node in source_node_index.values():
        source_node.mark_dirty_recursively(dirty_sources, dirty_headers)
    print("done.")

    #TODO: Sort dirty_sources for compile time (longest first).

    if dirty_sources:
        # precompile headers
        if dirty_headers:
            print("precompiling headers ...")
            compile_func = functools.partial(
                    _compile,
                    compiler_path=compiler_path,
                    target_name=target_name)
            sys.stdout.flush()
            for result in pool.imap_unordered(compile_func, dirty_headers):
                if result != 0:
                    exit(result)
            print("done.")


        # compile sources
        print("compiling sources ...")
        compile_func = functools.partial(
                _compile,
                compiler_path=compiler_path,
                target_name=target_name,
                get_output_path=pathhelpers.get_object_file_path,
                c_switch=True,
                include_pch=True)
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
