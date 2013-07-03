from os.path import getmtime, splitext, join

import cbob.project as project

class Node(object):
    # Our dependency graph for the source files is composed of these Nodes. They are used
    # to implement a directed acyclical graph (DAG) of file dependencies.
    # Whe use __slots__ instead of the standard __dict__ because there might be many files
    # and we want to save some memory here.
    __slots__ = ("file_path", "target_name", "dependencies", "last_dep_change")

    def __init__(self, file_path, target_name, is_source):
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


class BaseNode(object):
    __slots__ = ("path", "mtime", "dependencies")
    def __init__(self, path):
        self.path = path
        self.mtime = getmtime(path)
        self.dependencies = set()

class SourceNode(BaseNode):
    __slots__ = ("target", "object_path", "h_path", "gch_path")
    def __init__(self, path, target):
        super().__init__(path)
        self.target = target
        _project = project.get_project()
        objects_dir = join(target.path, "objects")
        precompiled_headers_dir = join(target.path, "precompiled_headers")
        mangled_path_base = splitext(_project.mangle_path(path))[0]
        self.object_path = join(objects_dir, mangled_path_base + ".o")
        self.h_path = join(precompiled_headers_dir, mangled_path_base + ".h")
        self.gch_path = join(precompiled_headers_dir, mangled_path_base + ".gch")

    def mark_dirty(self, dirty_source_nodes, dirty_header_nodes):
        try:
            object_mtime = getmtime(self.object_path)
        except OSError:
            object_mtime = 0

        # Shortcut if the source has no dependencies (rare, I presume)
        if not self.dependencies and self.mtime > object_mtime:
            dirty_source_nodes.append((self.path, self.object_path, None))
            return

        # Node has dependencies:
        try:
            gch_mtime = getmtime(self.gch_path)
        except OSError:
            gch_mtime = 0

        header_max_mtime = 0
        while self.dependencies and header_max_mtime <= object_mtime:
            node = self.dependencies.pop()
            header_max_mtime = max(header_max_mtime, node.get_max_mtime(object_mtime))

        all_max_mtime = max(header_max_mtime, self.mtime)
        if all_max_mtime > object_mtime:
            dirty_source_nodes.append((self.path, self.object_path, self.h_path))
            if header_max_mtime > gch_mtime:
                dirty_header_nodes.append((self.h_path, self.gch_path, None))

class HeaderNode(BaseNode):
    __slots__ = ("_max_mtime")
    def __init__(self, path):
        super().__init__(path)
        self._max_mtime = self.mtime

    def get_max_mtime(self, object_mtime):
        max_mtime = self._max_mtime
        while self.dependencies and max_mtime <= object_mtime:
            node = self.dependencies.pop()
            max_mtime = max(max_mtime, node.get_max_mtime(object_mtime))
        self._max_mtime = max_mtime
        return max_mtime
