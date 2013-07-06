from os.path import getmtime, splitext, join

import cbob.project as project

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
