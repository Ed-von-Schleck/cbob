import locale
import os
import os.path
import subprocess

import src.pathhelpers as pathhelpers
import src.checks as checks

class _Node(object):
    def __init__(self, file_name):
        self.file_name = file_name
        self._depends_on = set()
        self.depended_on_by = set()
        self.dirty = False

    def set_depends_on(self, nodes):
        self._depends_on = set(nodes)
        for node in nodes:
            node.depended_on_by.add(self)

    def mark_dirty_recursively(self):
        if not self.dirty:
            for node in self.depended_on_by:
                node.mark_dirty_recursively()
            self.dirty = True

    def clear_depends_on(self):
        for node in self._depends_on:
            node.depended_on_by.remove(self)
        self._depends_on.clear()

@checks.requires_configured
def build(target_name):

    project_root = pathhelpers.get_project_root()
    sources_dir = pathhelpers.get_sources_dir(target_name)
    build_dir = pathhelpers.get_build_dir(target_name)
    compiler_path = os.readlink(pathhelpers.get_compiler_symlink(target_name))
    linker_path = os.readlink(pathhelpers.get_linker_symlink(target_name))
    bindir_path = os.readlink(pathhelpers.get_bindir_symlink(target_name))
    gcc_path = pathhelpers.get_gcc_path()

    # dependency graph
    # generate node index
    node_index = {file_name: _Node(file_name) for file_name in os.listdir(sources_dir)}

    # build graph
    for file_name, node in node_index.items():
        file_path = os.readlink(os.path.join(sources_dir, file_name))
        norm_file_path = os.path.normpath(os.path.join(sources_dir, file_path))
        make_rule = subprocess.check_output([gcc_path, "-M", norm_file_path]).decode(locale.getpreferredencoding())
        source, sep, deps = make_rule.partition(":")
        dep_nodes = {node_index[os.path.relpath(dep, project_root).replace(os.sep, "_")] for dep in deps.split() if dep != "\\"}
        dep_nodes.remove(node_index[file_name])
        node_index[file_name].set_depends_on(dep_nodes)

    # check for files in need of recompilation
    for file_name, node in node_index.items():
        if node.dirty:
            continue # already marked for recompilation
        mtime = os.path.getmtime(os.path.join(sources_dir, file_name))
        try:
            build_file_path = os.path.join(build_dir, os.path.splitext(file_name)[0] + ".o")
            object_mtime = os.path.getmtime(build_file_path)
        except os.error as e:
            object_mtime = 0
        if mtime > object_mtime:
            node_index[file_name].mark_dirty_recursively()

    return_code = 0
    dirty_file_names = [file_name for file_name, node in node_index.items() if node.dirty]

    for file_name in dirty_file_names:
        object_file_name = os.path.splitext(file_name)[0] + ".o"
        object_file_path = os.path.join(build_dir, object_file_name)

        file_path = os.readlink(os.path.join(sources_dir, file_name))
        norm_file_path = os.path.normpath(os.path.join(sources_dir, file_path))

        cmd = [compiler_path, "-c", norm_file_path, "-o", object_file_path]
        print(" ".join(cmd))
        return_code = subprocess.call(cmd)
        if return_code != 0:
            exit(return_code)

    object_file_names = [os.path.join(build_dir, os.path.splitext(file_name)[0] + ".o") for file_name in node_index.keys()]
    cmd = [compiler_path, "-o", os.path.join(bindir_path, target_name)] + object_file_names
    print(" ".join(cmd))
    return_code = subprocess.call(cmd)
    if return_code != 0:
        exit(return_code)


