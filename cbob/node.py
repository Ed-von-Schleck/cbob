from hashlib import sha256 as hashfn
from itertools import zip_longest
import os
from os.path import getmtime, splitext, join, isfile

class BaseNode(object):
    #__slots__ = ("path", "mtime", "dependencies")
    def __init__(self, path):
        self.path = path
        self.mtime = getmtime(path)
        self.dependencies = set()

class SourceNode(BaseNode):
    #__slots__ = ("object_path", "h_path", "gch_path")
    def __init__(self, path, graph):
        super().__init__(path)
        _project = graph.target.project
        mangled_path_base = splitext(_project.mangle_path(path))[0]
        self._dirs = graph.target.dirs
        self._mangled_path_base = mangled_path_base
        self._includes = []
        self._finalized = False
        self._h_hash = None
        #self._content_hash = None
        with open(path, "r+b") as f:
            self._content_hash = hashfn(f.read()).hexdigest()

    @property
    def h_path(self):
        assert(self._h_hash is not None)
        return join(self._dirs.precompiled_headers, self._h_hash + ".h")

    @property
    def gch_path(self):
        assert(self._h_hash is not None)
        return join(self._dirs.precompiled_headers, self._h_hash + ".gch")

    @property
    def object_path(self):
        return join(self._dirs.objects, self._mangled_path_base + ".o")

    def add_include(self, include_path):
        assert(not self._finalized)
        self._includes.append("#include \"" + include_path + "\"\n")

    def finalize(self):
        assert(not self._finalized)
        self._h_hash = hashfn("".join(self._includes).encode("utf-8")).hexdigest()
        if not isfile(self.h_path):
            with open(self.h_path, "w") as uncompiled_header:
                uncompiled_header.writelines(self._includes)
        self._finalized = True

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
    #__slots__ = ("_max_mtime")
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
