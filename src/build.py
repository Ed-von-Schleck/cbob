import functools
import multiprocessing
import os
import os.path
import subprocess
import sys

import src.pathhelpers as pathhelpers
import src.checks as checks

class _Node(object):
    # Our dependency graph for the source files is composed of these Nodes. They are used
    # to implement a directed acyclical graph (DAG) of file dependencies.
    # Whe use __slots__ instead of the standard __dict__ because there might be many files
    # and we want to save some memory here.
    __slots__ = ("file_path", "target_name", "dependencies", "last_dep_change")

    def __init__(self, file_path, target_name):
        self.file_path = file_path
        self.target_name = target_name
        self.dependencies = set()
        self.last_dep_change = None

    def mark_dirty_recursively(self, dirty_sources, dirty_headers, object_mtime=None, depth=0):
        is_source = object_mtime is None
        if is_source:
            object_file_path = pathhelpers.get_object_file_path(self.target_name, self.file_path)
            object_mtime = os.path.getmtime(object_file_path) if os.path.isfile(object_file_path) else 0

            precompiled_header_path = pathhelpers.get_precompiled_header_path(self.target_name, self.file_path)
            precompiled_header_mtime = os.path.getmtime(precompiled_header_path) if os.path.isfile(precompiled_header_path) else -1

        # We need to check the headers even if the source is dirty, because we might need to
        # re-precompile the headers too. To make sure the loop enters, we query the `mtime` of the source after
        # the recursive walk over the headers returns. If this node is *not* the source, but a header, we *do*
        # get the `mtime`. However, if that property has already been set by a previous walk, we take that instead.
        self.last_dep_change = 0 if is_source else self.last_dep_change if self.last_dep_change is not None else os.path.getmtime(self.file_path)

        # The walk itself is destructive, so that every dependency is only visited once *ever*. This makes this algorithm
        # O(N). Chances are, however, that not all nodes have to be visited, because we return as soon as one header (or
        # it's dependencies) is newer than the corresponding object file.
        while self.dependencies and self.last_dep_change <= object_mtime:
            node = self.dependencies.pop()
            node_last_dep_change = node.mark_dirty_recursively(dirty_sources, dirty_headers, object_mtime, depth + 1)
            self.last_dep_change = max(node_last_dep_change, self.last_dep_change)
        
        # When we are back at the start, we first look if the source needs to be recompiled. Only then we consider recompiling
        # the headers, too.
        if is_source:
            last_change = max(self.last_dep_change, os.path.getmtime(self.file_path))
            if last_change > object_mtime:
                dirty_sources.add(self.file_path)
                if self.last_dep_change > precompiled_header_mtime:
                    uncompiled_header_path = pathhelpers.get_uncompiled_header_path(self.target_name, self.file_path)
                    dirty_headers.add(uncompiled_header_path)
            self.last_dep_change = last_change

        return self.last_dep_change


def _compile(file_path, compiler_path, target_name, c_switch=False, get_output_path=None, include_pch=False):
    # This function is later used as a partial (curried) function, with the `file_path` parameter being mapped
    # to a list of files to compile.
    print(" ", file_path)
    cmd = [compiler_path, file_path]
    if get_output_path is not None:
        cmd += ["-o", get_output_path(target_name, file_path)]
    if c_switch:
        cmd.append("-c")
    if include_pch:
        cmd += ["-fpch-preprocess", "-include", pathhelpers.get_uncompiled_header_path(target_name, file_path)]

    process = subprocess.Popen(cmd)
    return process.wait()

def _get_dep_info(file_path):
    # The options used:
    # * -H: prints the dotted header information
    # * -w: suppressed warnings
    # * -E: makes GCC stop after the preprocessing (no compilation)
    # * -P: removes comments
    cmd = (pathhelpers.get_gcc_path(), "-H", "-w", "-E", "-P", file_path)
    # For some reason gcc outputs the header information over `stderr`.
    # Not that this is documented anywhere ...
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
        out, err = process.communicate()
    # The output looks like
    #     . inc1.h
    #     .. inc1inc1.h
    #     . inc2.h
    # etc., with inc1inc1.h being included by inc1.h. In other words, the number of dots
    # indicates the level of nesting. Also, there are lots of lines of no interest to us.
    # Let's ignore them.
    raw_deps = (line.partition(" ") for line in err.split("\n") if line and line[0] == ".")
    deps = [(len(dots), os.path.normpath(rest)) for (dots, sep, rest) in raw_deps]
    return file_path, deps

@checks.requires_target_exists
def build(target_name, jobs):
    # Let's build a target! But before that, process all target dependencies
    # recursively to make sure they are up to date.
    dependencies_dir = pathhelpers.get_dependencies_dir(target_name)
    for dep in os.listdir(dependencies_dir):
        print("Building dependency '{}'.".format(dep))
        build(dep, jobs)
        print("Done building dependency '{}'".format(dep))
        print()
    build_target(target_name, jobs)

@checks.requires_target_exists
def build_target(target_name, jobs):
    # Bail out if there are no sources -
    # there is no need for a virtual target to be fully configured.
    sources_links = os.listdir(pathhelpers.get_sources_dir(target_name))
    if sources_links:
        _do_build_target(target_name, jobs, sources_links)
    else:
        print("No sources - nothing to do.")

@checks.requires_configured
def _do_build_target(target_name, jobs, sources_links=None):
    # Here the actual heavy lifting happens.
    # First off, if a `jobs` parameter is given, it's passed on from the argument parser as a list.
    # We take the first element of it. If its `None`, then `multiprocessing.Pool` will use as many
    # processes as there are CPUs.
    if jobs is not None:
        jobs = jobs[0]
    sources_dir = pathhelpers.get_sources_dir(target_name)
    compiler_path = os.readlink(pathhelpers.get_compiler_symlink(target_name))
    linker_path = os.readlink(pathhelpers.get_linker_symlink(target_name))
    pool = multiprocessing.Pool(jobs)

    # The `sources_list` parameter is just so that we don't have to touch the `sources` directory twice, if we
    # have listed its content before.
    print("calculating dependencies ...", end=" ")
    sys.stdout.flush()
    if sources_links is not None:
        sources = [pathhelpers.get_source_path_from_symlink(target_name, source) for source in sources_links]
    else:
        sources = [pathhelpers.get_source_path_from_symlink(target_name, source) for source in os.listdir(sources_dir)]

    # We have two indexes: The `source_node_index` points, well, to the source nodes, while the `node_index` points to
    # all nodes. Later we use the nodes in the `source_node_index` as root nodes for starting the search for dirty nodes.
    source_node_index = {file_path: _Node(file_path, target_name) for file_path in sources}
    node_index = source_node_index.copy()

    # This is somewhat straight-forward if you have ever written a stream-parser (like SAX), though it adds a twist
    # in that we save references to processed nodes in a set. It may be a bit unintuitive that we only skip a node 
    # if it was in another node's dependencies - but note how, when we process a node, we don't add an edge to that
    # very node, but to the node one layer *down* in the stack. Think about it for a while, then it makes sense.
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
        processed_nodes |= node.dependencies

        # For every source file, we generate a corresponding `.h` file that consists of all the
        # `#include`s of that source file. This is the `uncompiled_header`. It is saved in one
        # of *cbob*s mysterious directories. After we processed a source file, we check if it is
        # up to date. We are doing that with a set comparison, because we are interested in *semantic*,
        # not byte-for-byte equality (if that turns out to be overly slow, it can be replaced with
        # a line-by-line comparison with a list).
        uncompiled_header_path = pathhelpers.get_uncompiled_header_path(target_name, file_path)
        changed = False
        try:
            with open(uncompiled_header_path, "r") as uncompiled_header:
                if includes.symmetric_difference(uncompiled_header):
                    changed = True
        except IOError:
            changed = True

        # It the uncompiled header file changed, we save it and delete any existing precompiled header.
        if changed:
            with open(uncompiled_header_path, "w") as uncompiled_header:
                uncompiled_header.writelines(includes)
                
            precompiled_header_path = pathhelpers.get_precompiled_header_path(target_name, file_path)
            try:
                os.remove(precompiled_header_path)
            except OSError:
                pass
    print("done.")

    print("determining files for recompilation ...", end=" ")
    sys.stdout.flush()

    dirty_sources = set()
    dirty_headers = set()
    for source_node in source_node_index.values():
        # This starts a depth-first recursive search for dirty (changed) source and header files.
        # See the function comments for explanation.
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
        cmd = [linker_path, "-o", bin_path] + object_file_names
        print("linking ...")
        print(" ", bin_path)
        sys.stdout.flush()
        return_code = subprocess.call(cmd)
        if return_code != 0:
            exit(return_code)
        print("done.")
    else:
        print("Nothing to do.")
