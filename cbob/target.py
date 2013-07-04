from functools import partial
import logging
from itertools import zip_longest
import os
from os.path import basename, join, islink, normpath, abspath, isdir, relpath
import subprocess

from cbob.pathhelpers import read_symlink, mangle_path, expand_glob, make_rel_symlink
from cbob.definitions import SOURCE_FILE_EXTENSIONS

class Target(object):
    __slots__ = ("path", "name", "_sources", "project", "_dependencies", "_compiler", "_linker", "_bin_dir", "_language")

    def __init__(self, path, project):
        self.path = path
        self.name = basename(path)
        self.project = project
        self._sources = None
        self._dependencies = None
        self._compiler = None
        self._linker = None
        self._bin_dir = None
        self._language = None

    @property
    def sources(self):
        if self._sources is None:
            sources_dir = join(self.path, "sources")
            self._sources = [read_symlink(name, sources_dir) for name in os.listdir(sources_dir)]
        return self._sources

    @property
    def dependencies(self):
        if self._dependencies is None:
            dependencies_dir = join(self.path, "dependencies")
            self._dependencies = {name: Target(read_symlink(name, dependencies_dir), self.project) for name in os.listdir(dependencies_dir)}
        return self._dependencies

    @property
    def compiler(self):
        if self._compiler is None:
            try:
                self._compiler = os.readlink(join(self.path, "compiler"))
            except OSError:
                return None
        return self._compiler

    @property
    def linker(self):
        if self._linker is None:
            try:
                self._linker = os.readlink(join(self.path, "linker"))
            except OSError:
                return None
        return self._linker

    @property
    def bin_dir(self):
        if self._bin_dir is None:
            try:
                self._bin_dir= os.readlink(join(self.path, "bin_dir"))
            except OSError:
                return None
        return self._bin_dir

    @property
    def language(self):
        if self._language is None:
            self._language = self._guess_target_language()
        return self._language

    def add_sources(self, source_globs):
        sources_dir = join(self.path, "sources")
        added_file_names = []
        for file_list in expand_glob(source_globs):
            for file_name, abs_file_path, symlink_path in self.project.iter_file_list(file_list, sources_dir):
                if not os.path.splitext(file_name)[1] in SOURCE_FILE_EXTENSIONS:
                    logging.warning("'{}' does not seem to be a C/C++ source file (ending is not one of {}).".format(file_name, ", ".join(SOURCE_FILE_EXTENSIONS)))
                    continue
                if islink(symlink_path):
                    logging.debug("File '{}' is already a source file of target '{}'.".format(file_name, self.name))
                    continue
                added_file_names.append(file_name)
                make_rel_symlink(abs_file_path, symlink_path)

        added_files_count = len(added_file_names)
        if added_files_count == 0:
            logging.warning("No files have been added to target '{}'.".format(self.name))
        elif added_files_count == 1:
            logging.info("File '{}' has been added to target '{}'.".format(added_file_names[0], self.name))
        else:
            logging.info("Files added to target '{}':\n  {}".format(self.name, "\n  ".join(added_file_names)))
        self._sources = None
    
    def remove_sources(self, source_globs):
        sources_dir = join(self.path, "sources")
        removed_file_names = []
        for file_list in expand_glob(source_globs):
            for file_name, rel_file_path, symlink_path in self.project.iter_file_list(file_list, sources_dir):
                try:
                    os.unlink(symlink_path)
                except OSError:
                    logging.debug("File '{}' not a source file of target '{}'.".format(file_name, self.name))
                    continue
                removed_file_names.append(file_name)

        removed_files_count = len(removed_file_names)
        if removed_files_count == 0:
            logging.warning("No files have been removed from to target '{}'.".format(self.name))
        elif removed_files_count == 1:
            logging.info("File '{}' has been removed from target '{}'.".format(removed_file_names[0], self.name))
        else:
            logging.info("Files removed from target '{}':\n  {}".format(self.name, "\n  ".join(added_file_names)))
        self._sources = None


    def show_sources(self):
        for file_name in self.sources:
            print(file_name)

    def depend_on(self, dependencies):
        targets_dir = join(self.project.root_path, ".cbob", "targets")
        dependencies_dir = join(self.path, "dependencies")
        for dep in dependencies:
            if dep in self.dependencies:
                logging.warning("Target '{}' is already a dependency of target '{}'.".format(dep, self.name))
                continue
            dep_path = join(targets_dir, dep)
            dep_symlink = join(dependencies_dir, dep)
            if not isdir(dep_path):
                from cbob.error import TargetDoesntExistError
                raise TargetDoesntExistError(dep)
            make_rel_symlink(dep_path, dep_symlink)
        self._dependencies = None

    def build(self, jobs):
        for dep in self.dependencies:
            logging.info("Building dependency '{}'.".format(dep))
            dep.build(jobs)
            logging.info("Done building dependency '{}'".format(dep))
        self._build_self(jobs)

    def _build_self(self, jobs):
        # Bail out if there are no sources -
        # there is no need for a virtual target to be fully configured.
        sources = self.sources
        if not sources:
            logging.info("No sources - nothing to do.")
            return

        import multiprocessing
        from cbob.node import SourceNode, HeaderNode
        # Here the actual heavy lifting happens.
        # First off, if a `jobs` parameter is given, it's passed on from the argument parser as a list.
        # We take the first element of it. If its `None`, then `multiprocessing.Pool` will use as many
        # processes as there are CPUs.
        if jobs is not None:
            jobs = jobs[0]

        pool = multiprocessing.Pool(jobs)

        logging.info("calculating dependencies ...")
        # One might argue that a 'Graph' class should exists and a corresponding 'graph' object shoudl be
        # instanciated here. Tried it; it's somewhat painful to make it reasonably self-contained (needs
        # to know about configuration when reading header output from the gcc, which it needs to
        # know about, ...).

        # We have two indexes: The `source_node_index` points, well, to the source nodes, while the `node_index` points to
        # all nodes. Later we use the nodes in the `source_node_index` as root nodes for starting the search for dirty nodes.
        source_node_index = {file_path: SourceNode(file_path, self) for file_path in sources}
        #node_index = source_node_index.copy()
        header_node_index = {}

        # This is somewhat straight-forward if you have ever written a stream-parser (like SAX), though it adds a twist
        # in that we save references to processed nodes in a set. It may be a bit unintuitive that we only skip a node 
        # if it was in another node's dependencies - but note how, when we process a node, we don't add an edge to that
        # very node, but to the node one layer *down* in the stack. Think about it for a while, then it makes sense.
        gcc_path = self.project.gcc_path
        processed_nodes = set()

        get_dep_info = partial(_get_dep_info, gcc_path=self.project.gcc_path)
        for file_path, deps in pool.imap_unordered(get_dep_info, sources):
            node = source_node_index[file_path]
            parent_nodes_stack = [node]

            includes = []

            for current_depth, dep_path in deps:
                includes.append("#include \"" + dep_path + "\"\n")
                if dep_path in header_node_index:
                    current_node = header_node_index[dep_path]
                    if current_node in processed_nodes:
                        continue
                    processed_nodes |= current_node.dependencies
                else:
                    current_node = HeaderNode(dep_path)
                    header_node_index[dep_path] = current_node

                parent_nodes_stack[:] = parent_nodes_stack[:current_depth]
                parent_nodes_stack[-1].dependencies.add(current_node)
                parent_nodes_stack.append(current_node)
            processed_nodes |= node.dependencies

            # For every source file, we generate a corresponding `.h` file that consists of all the
            # `#include`s of that source file. This is the `node.h_path`. It is saved in one
            # of *cbob*s mysterious directories. After we processed a source file, we check if it is
            # up to date by doing a line-by-line comparison with a newly created `#include` list.
            changed = False
            try:
                with open(node.h_path, "r") as uncompiled_header:
                    for newline, oldline in zip_longest(includes, uncompiled_header):
                        if newline != oldline:
                            changed = True
                            break
            except IOError:
                changed = True

            # It the uncompiled header file changed, we save it and delete any existing precompiled header.
            if changed:
                with open(node.h_path, "w") as uncompiled_header:
                    uncompiled_header.writelines(includes)
                    
                try:
                    os.remove(node.gch_path)
                except OSError:
                    # It's OK if it didn't work; it just means that it wasn't there in the first place
                    pass
        logging.info("done.")

        logging.info("determining files for recompilation ...")
        dirty_sources = []
        dirty_headers = []
        for source_node in source_node_index.values():
            source_node.mark_dirty(dirty_sources, dirty_headers)
        logging.info("done.")

        if dirty_sources:
            # precompile headers
            if dirty_headers:
                logging.info("precompiling headers ...")
                compile_func = partial(
                        _compile,
                        compiler_path=self.compiler,
                        target_name=self.name)
                for result in pool.imap_unordered(compile_func, dirty_headers):
                    if result != 0:
                        exit(result)
                logging.info("done.")

            # compile sources
            logging.info("compiling sources ...")
            compile_func = partial(
                    _compile,
                    compiler_path=self.compiler,
                    target_name=self.name,
                    c_switch=True,
                    include_pch=True)
            for result in pool.imap_unordered(compile_func, dirty_sources):
                if result != 0:
                    from cbob.error import CbobError
                    raise CbobError("compilation failed")
                    
            logging.info("done.")

            # link
            object_file_names = [node.object_path for node in source_node_index.values()]
            bin_path = join(self.bin_dir, self.name)
            cmd = [self.linker, "-o", bin_path] + object_file_names
            logging.info("linking ...")
            logging.info(" ", bin_path)
            return_code = subprocess.call(cmd)
            if return_code != 0:
                from cbob.error import CbobError
                raise CbobError("linking failed")
            logging.info("done.")
        else:
            logging.info("Nothing to do.")

    def _guess_target_language(self):
        for file_name in self.sources:
            root, ext = os.path.splitext(file_name)
            ext = ext.lower()
            if ext == ".c":
                return "C"
            elif ext in (".cc", ".cpp", "c++", ".cxx"):
                return "C++"
        return None



    def configure(self, auto, force, compiler, linker, bin_dir):
        if compiler is not None:
            os.symlink(compiler, join(self.path, "compiler"))
            self._compiler = None
        if linker is not None:
            os.symlink(linker, join(self.path, "linker"))
            self._linker = None
        if bin_dir is not None:
            os.symlink(bin_dir, join(self.path, "bin_dir"))
            self._bin_dir = None
        if auto:
            if compiler is None:
                if self.compiler is not None and not force:
                    logging.warning("There's already a compiler configured. Use '--force' to overwrite current configuration")
                else:
                    try:
                        if self.language is "C":
                            compiler_path = subprocess.check_output(["which", "gcc"]).strip()
                        elif lang == "C++":
                            compiler_path = subprocess.check_output(["which", "g++"]).strip()
                        else:
                            from cbob.error import CbobError
                            raise CbobError("unable to guess the language of the target's sources. Please configure manually")
                    except subprocess.CalledProcessError:
                        from cbob.error import CbobError
                        raise CbobError("no compiler for language '{}' found (might be cbob's fault).".format(self.language))
                    compiler_symlink = join(self.path, "compiler")
                    if self.compiler is not None and force:
                        os.unlink(compiler_symlink)
                    os.symlink(compiler_path, compiler_symlink)
                    self._compiler = None
            if linker is None:
                if self.linker is not None and not force:
                    logging.warning("There's already a linker configured. Use '--force' to overwrite current configuration")
                else:
                    linker_symlink = join(self.path, "linker")
                    if self.linker is not None and force:
                        os.unlink(linker_symlink)
                    os.symlink(self.compiler, linker_symlink)
                    self._linker = None
            if bin_dir is None:
                if self.bin_dir is not None and not force:
                    logging.warning("There's already a binary output directory configured. Use '--force' to overwrite current configuration")
                else:
                    bin_dir_symlink = join(self.path, "bin_dir")
                    if self.bin_dir is not None and force:
                        os.unlink(bin_dir_symlink)
                    assumed_bindir = os.path.join(self.project.root_path, "bin")
                    bindir_auto = assumed_bindir if os.path.isdir(assumed_bindir) else self.project.root_path
                    os.symlink(bindir_auto, bin_dir_symlink)
                    self._bin_dir = None
        logging.info("compiler: '{}', "
                     "linker: '{}', "
                     "binary output directory: '{}'".format(self.compiler, self.linker, self.bin_dir))


def _get_dep_info(file_path, gcc_path):
    # The options used:
    # * -H: prints the dotted header information
    # * -w: suppressed warnings
    # * -E: makes GCC stop after the preprocessing (no compilation)
    # * -P: removes comments
    cmd = (gcc_path, "-H", "-w", "-E", "-P", file_path)
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

def _compile(source, compiler_path, target_name, c_switch=False, include_pch=False):
    # This function is later used as a partial (curried) function, with the `file_path` parameter being mapped
    # to a list of files to compile.
    source_path, output_path, h_path = source
    print(" ", source_path)
    cmd = [compiler_path, source_path, "-o", output_path]
    if c_switch:
        cmd.append("-c")
    if include_pch and h_path is not None:
        cmd += ["-fpch-preprocess", "-include", h_path]

    process = subprocess.Popen(cmd)
    return process.wait()
