from functools import partial
import logging
from itertools import zip_longest
import os
from os.path import basename, join, islink, normpath, abspath, isdir, isfile, relpath, commonprefix, expandvars, split, splitext
#import pickle
import subprocess

from cbob.pathhelpers import read_symlink, expand_glob, make_rel_symlink, print_information
from cbob.definitions import SOURCE_FILE_EXTENSIONS, HOOKS
from cbob.node import SourceNode, HeaderNode

class Target(object):
    __slots__ = ("path", "name", "_sources", "project", "_dependencies", "_compiler", "_linker", "_bin_dir", "_language", "_plugins")

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
        self._plugins = None

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
            if not isdir(dependencies_dir):
                from cbob.error import NotConfiguredError
                raise NotConfiguredError(self.name)

            import cbob.project
            raw_dep_names = os.listdir(dependencies_dir)
            self._dependencies = {}
            for raw_dep_name in raw_dep_names:
                *subproject_names, dep_name = raw_dep_name.split(".")
                _project = cbob.project.get_project(subproject_names)
                self._dependencies[raw_dep_name] = _project.targets[dep_name]
        return self._dependencies

    @property
    def compiler(self):
        if self._compiler is None:
            try:
                self._compiler = os.readlink(join(self.path, "compiler"))
            except OSError as e:
                from cbob.error import NotConfiguredError
                raise NotConfiguredError(self.name) from e
        return self._compiler

    @property
    def linker(self):
        if self._linker is None:
            try:
                self._linker = os.readlink(join(self.path, "linker"))
            except OSError as e:
                from cbob.error import NotConfiguredError
                raise NotConfiguredError(self.name) from e
        return self._linker

    @property
    def bin_dir(self):
        if self._bin_dir is None:
            try:
                self._bin_dir= os.readlink(join(self.path, "bin_dir"))
            except OSError as e:
                from cbob.error import NotConfiguredError
                raise NotConfiguredError(self.name) from e
        return self._bin_dir

    @property
    def language(self):
        if self._language is None:
            self._language = self._guess_target_language()
        return self._language

    @property
    def plugins(self):
        if self._plugins is None:
            import imp
            plugins_dir = join(self.path, "plugins")
            self._plugins = dict.fromkeys(HOOKS, [])
            if not isdir(plugins_dir):
                from cbob.error import NotConfiguredError
                raise NotConfiguredError(self.name) from e
            for filename in os.listdir(plugins_dir):
                abs_filename = read_symlink(filename, plugins_dir)
                path, filename = os.path.split(abs_filename)
                name, ext = splitext(filename)
                fp, fn, desc = imp.find_module(name, [path])
                plugin_module = imp.load_module(name, fp, fn, desc)
                hooks = [func for func in dir(plugin_module) if func in HOOKS]
                for hook in hooks:
                    plugin_func = getattr(plugin_module, hook)
                    if self._plugins[hook]:
                        self._plugins[hook].append(plugin_func)
                    else:
                        self._plugins[hook] = [plugin_func]
        return self._plugins
            

    def add_sources(self, source_globs):
        self.run_plugins("pre_add")
        sources_dir = join(self.path, "sources")
        added_file_names = []
        for file_list in expand_glob(source_globs):
            for file_name, abs_file_path, symlink_path in self.project.iter_file_list(file_list, sources_dir):
                if not splitext(file_name)[1] in SOURCE_FILE_EXTENSIONS:
                    logging.warning("'{}' does not seem to be a C/C++ source file (ending is not one of {}).".format(file_name, ", ".join(SOURCE_FILE_EXTENSIONS)))
                    continue
                if islink(symlink_path):
                    logging.debug("File '{}' is already a source file of target '{}'.".format(file_name, self.name))
                    continue
                root_path = self.project.root_path
                if commonprefix((abs_file_path, root_path)) != root_path:
                    logging.warning("File '{}' is not in a (sub)-direcory of the project.".format(file_name))
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
        self.run_plugins("post_add")
    
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
            logging.warning("No files have been removed from target '{}'.".format(self.name))
        elif removed_files_count == 1:
            logging.info("File '{}' has been removed from target '{}'.".format(removed_file_names[0], self.name))
        else:
            logging.info("Files removed from target '{}':\n  {}".format(self.name, "\n  ".join(removed_file_names)))
        self._sources = None


    def show(self, all_, sources, dependencies):
        if not sources and not dependencies:
            all_ = True
        if all_ or sources:
            print_information("Sources", self.sources)
            print()
        if all_ or dependencies:
            print_information("Dependencies", self.dependencies)

    def depend_on(self, dependencies):
        import cbob.project
        dependencies_dir = join(self.path, "dependencies")
        for raw_dep in dependencies:
            if raw_dep in self.dependencies:
                logging.warning("Target '{}' is already a dependency of target '{}'.".format(raw_dep, self.name))
                continue
            *subprojects, dep_name = raw_dep.split(".")
            dep_project = cbob.project.get_project(subprojects)
            targets_dir = join(dep_project.root_path, ".cbob", "targets")

            dep_path = join(targets_dir, dep_name)
            dep_symlink = join(dependencies_dir, raw_dep)
            if not isdir(dep_path):
                from cbob.error import TargetDoesntExistError
                raise TargetDoesntExistError(dep)
            make_rel_symlink(dep_path, dep_symlink)
        self._dependencies = None

    def register(self, plugins):
        plugins_dir = join(self.path, "plugins")
        added_plugins = []
        for file_list in expand_glob(plugins):
            for file_name, abs_file_path, symlink_path in self.project.iter_file_list(file_list, plugins_dir):
                if abs_file_path in self.plugins:
                    logger.warning("'{}' is already a plugin of target '{}'.".format(plugin, self.name))
                    continue
                added_plugins.append(file_name)
                make_rel_symlink(abs_file_path, symlink_path)

        added_plugins_count = len(added_plugins)
        if added_plugins_count == 0:
            logging.warning("No plugins has been registered for target '{}'.".format(self.name))
        elif added_plugins_count == 1:
            logging.info("Plugin '{}' has been registered for target '{}'.".format(added_plugins[0], self.name))
        else:
            logging.info("Plugins registered for target '{}':\n  {}".format(self.name, "\n  ".join(added_plugins)))

        self._plugins = None
        

    def build(self, jobs, oneshot, keep_going):
        for dep_name, dep_target in self.dependencies.items():
            logging.info("Building dependency '{}'.".format(dep_name))
            dep_target.build(jobs, oneshot, keep_going)
            logging.info("Done building dependency '{}'".format(dep_name))
        self._build_self(jobs, oneshot, keep_going)

    def _build_self(self, jobs, oneshot, keep_going):
        self.run_plugins("pre_build")
        #for plugin in self.plugins.values():
        #    if hasattr(plugin, "pre_build"):
        #        plugin.pre_build(self)
        # Bail out if there are no sources -
        # there is no need for a virtual target to be fully configured.
        sources = self.sources
        if not sources:
            logging.info("No sources - nothing to do.")
            return
        
        if self.compiler is None or self.linker is None or self.bin_dir is None:
            from cbob.error import NotConfiguredError
            raise NotConfiguredError(self.name)

        # Here the actual heavy lifting happens.
        # First off, if a `jobs` parameter is given, it's passed on from the argument parser as a list.
        # We take the first element of it. If its `None`, then `multiprocessing.Pool` will use as many
        # processes as there are CPUs.
        if jobs is not None:
            jobs = jobs[0]

        #TODO: Profile if a `ProcessPool` might be better (that's doubtful, though).
        #TODO: Investigate if the `concurrent.future` package might offer some advantage.
        from multiprocessing.pool import ThreadPool
        pool = ThreadPool(jobs)
        
        logging.info("calculating dependencies ...")
        # One might argue that a 'Graph' class should exists and a corresponding 'graph' object should be
        # instanciated here. Tried it; it's somewhat painful to make it reasonably self-contained (needs
        # to know about configuration when reading header output from the gcc, which it needs to
        # know about, ...).

        source_nodes = self._calculate_dependencies(oneshot, pool)
        logging.info("done.")

        logging.info("determining files for recompilation ...")
        dirty_sources = []
        dirty_headers = []

        # Walk the dependency tree to find dirty sources and '.h'-files,
        # unless the oneshot option is given, in which case all sources and corresping '.h'-files
        # are marked for recompilation.
        if not oneshot:
            for source_node in source_nodes:
                source_node.mark_dirty(dirty_sources, dirty_headers)
        else:
            for source_node in source_nodes:
                dirty_sources.append((source_node.path, source_node.object_path, source_node.h_path))
                dirty_headers.append((source_node.h_path, source_node.gch_path, None))
        logging.info("done.")

        bin_path = join(self.bin_dir, self.name)
        is_bin_dirty = len(dirty_sources) > 0 or not isfile(bin_path)
        failed = False

        if dirty_sources:
            # precompile headers
            if dirty_headers:
                logging.info("precompiling headers ...")
                compile_func = partial(
                        _compile,
                        compiler_path=self.compiler)
                for source_file, result in pool.imap_unordered(compile_func, dirty_headers):
                    if result != 0:
                        if keep_going:
                            logging.warning("compilation of header '{}' failed".format(source_file))
                            failed = True
                        else:
                            exit(result)
                logging.info("done.")

            # compile sources
            logging.info("compiling sources ...")
            compile_func = partial(
                    _compile,
                    compiler_path=self.compiler,
                    c_switch=True,
                    include_pch=True)
            for source_file, result in pool.imap_unordered(compile_func, dirty_sources):
                if result != 0:
                    if keep_going:
                        logging.warning("compilation of file '{}' failed".format(source_file))
                        failed = True
                    else:
                        from cbob.error import CbobError
                        raise CbobError("compilation of file '{}' failed".format(source_file))
                    
            logging.info("done.")

        if is_bin_dirty:
            if failed:
                from cbob.error import CbobError
                raise CbobError("skip linking because of compilation errors")
            # link
            object_file_names = [node.object_path for node in source_nodes]
            cmd = [self.linker, "-o", bin_path] + object_file_names
            logging.info("linking ...")
            logging.info("  " + bin_path)
            return_code = subprocess.call(cmd)
            if return_code != 0:
                from cbob.error import CbobError
                raise CbobError("linking failed")
            logging.info("done.")
        else:
            logging.info("Nothing to do.")
        self.run_plugins("post_build")
        #for plugin in self.plugins.values():
        #    if hasattr(plugin, "post_build"):
        #        plugin.pre_build(self)

    def _calculate_dependencies(self, oneshot, pool):
        source_node_index = {}
        header_node_index = {}
        #depgraph_file_name = join(self.path, "depgrap")
        #try:
        #    with open(depgraph_file_name, "rb") as depgraph_file:
        #        old_source_node_index, old_header_node_index = pickle.load(depgraph_file)
        #except IOError:
        #    old_source_node_index = {}
        #    old_header_node_index = {}

        # This is somewhat straight-forward if you have ever written a stream-parser (like SAX) in that we maintain a stack
        # of where we currently sit in the tree.
        # It adds a twist, though, in that we save references to processed nodes in a set. It may be a bit unintuitive that
        # we only skip a node if it was in another node's dependencies - but note how, when we process a node, we don't add
        # an edge to that very node, but to the node one layer *down* in the stack. Think about it for a while, then it makes
        # sense.
        processed_nodes = set() if not oneshot else None

        get_dep_info = partial(_get_dep_info, gcc_path=self.project.gcc_path)
        for file_path, deps in pool.imap_unordered(get_dep_info, self.sources):
            node = SourceNode(file_path, self)
            source_node_index[file_path] = node
            parent_nodes_stack = [node]

            includes = []

            for current_depth, dep_path in deps:
                includes.append("#include \"" + dep_path + "\"\n")
                if oneshot:
                    continue
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

            # For every source file, we generate a corresponding `.h` file that consists of all the
            # `#include`s of that source file. This is the `node.h_path`. It is saved in one
            # of *cbob*s mysterious directories. After we processed a source file, we check if it is
            # up to date by doing a line-by-line comparison with a newly created `#include` list.
            if not oneshot:
                overwrite_header = False
                try:
                    with open(node.h_path, "r") as uncompiled_header:
                        for newline, oldline in zip_longest(includes, uncompiled_header):
                            if newline != oldline:
                                overwrite_header = True
                                break
                except IOError:
                    overwrite_header = True
            else:
                overwrite_header = True

            # It the uncompiled header file changed, we save it and delete any existing precompiled header.
            if overwrite_header:
                with open(node.h_path, "w") as uncompiled_header:
                    uncompiled_header.writelines(includes)
                try:
                    os.remove(node.gch_path)
                except OSError:
                    # It's OK if it didn't work; it just means that it wasn't there in the first place
                    pass
        #with open(depgraph_file_name, "wb") as depgraph_file:
        #    depgraph = (source_node_index, header_node_index)
        #    pickle.dump(depgraph, depgraph_file, pickle.HIGHEST_PROTOCOL)
        return source_node_index.values()

    def _guess_target_language(self):
        for file_name in self.sources:
            root, ext = splitext(file_name)
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
                compiler_symlink = self._check_prepare_symlink("compiler", "compiler", force)
                if compiler_symlink is not None:
                    compiler_path = self._find_compiler_path()
                    os.symlink(compiler_path, compiler_symlink)
                    self._compiler = None
            if linker is None:
                linker_symlink = self._check_prepare_symlink("linker", "linker", force)
                if linker_symlink is not None:
                    os.symlink(self.compiler, linker_symlink)
                    self._linker = None
            if bin_dir is None:
                bin_dir_symlink = self._check_prepare_symlink("bin_dir", "binary output directory", force)
                if bin_dir_symlink is not None:
                    assumed_bindir = join(self.project.root_path, "bin")
                    bindir_auto = assumed_bindir if isdir(assumed_bindir) else self.project.root_path
                    os.symlink(bindir_auto, bin_dir_symlink)
                    self._bin_dir = None
        logging.info("compiler: '{}', "
                     "linker: '{}', "
                     "binary output directory: '{}'".format(self.compiler, self.linker, self.bin_dir))

    def _check_prepare_symlink(self, name, description, force):
        symlink = join(self.path, name)
        symlink_exists = islink(symlink)
        if symlink_exists and not force:
            logging.warning("There's already a {} configured. Use '--force' to overwrite current configuration".format(description))
            return None
        else:
            if symlink_exists and force:
                os.unlink(symlink)
            return symlink


    def _find_compiler_path(self):
        try:
            if self.language is "C":
                path_from_var = expandvars("$CC")
                if path_from_var != "$CC":
                    logging.debug("determined C compiler path from $CC environment variable")
                    compiler_path = path_from_var
                else:
                    logging.debug("determined C compiler path from `which gcc`")
                    compiler_path = subprocess.check_output(["which", "gcc"]).strip()
            elif lang == "C++":
                if path_from_var != "$CXX":
                    logging.debug("determined C compiler path from $CXX environment variable")
                    compiler_path = path_from_var
                else:
                    logging.debug("determined C compiler path from `which g++`")
                    compiler_path = subprocess.check_output(["which", "g++"]).strip()
            else:
                from cbob.error import CbobError
                raise CbobError("unable to guess the language of the target's sources. Please configure manually")
        except subprocess.CalledProcessError:
            from cbob.error import CbobError
            raise CbobError("no compiler for language '{}' found (might be cbob's fault).".format(self.language))
        return compiler_path

    def _clean_dir(self, dirname):
        dir_path = join(self.path, dirname)
        for file_name in os.listdir(dir_path):
            file_path = join(dir_path, file_name)
            os.remove(file_path)
            logging.debug("removed file '{}'".format(file_name))


    def clean(self, all_, object_files, pch_files, bin_file):
        if all_ or object_files:
            self._clean_dir("objects")
            logging.info("cleaned object files")
        if all_ or pch_files:
            self._clean_dir("precompiled_headers")
            logging.info("cleaned precompiled header files")
        if all_ or bin_file:
            bin_path = join(self.bin_dir, self.name)
            try:
                os.remove(bin_path)
                logging.debug("removed binary file '{}'".format(bin_path))
            except OSError:
                logging.debug("no binary file to remove")
            logging.info("cleaned binary file")

    def run_plugins(self, hookname):
        logging.debug("running '{}' plugin functions".format(hookname))
        for func in self.plugins[hookname]:
            logging.debug("running plugin function '{}'".format(func))
            func(self)



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

def _compile(source, compiler_path, c_switch=False, include_pch=False):
    # This function is later used as a partial (curried) function, with the `file_path` parameter being mapped
    # to a list of files to compile.
    source_path, output_path, h_path = source
    logging.info("  " + source_path)
    cmd = [compiler_path, source_path, "-o", output_path]
    if c_switch:
        cmd.append("-c")
    if include_pch and h_path is not None:
        cmd += ["-fpch-preprocess", "-include", h_path]

    process = subprocess.Popen(cmd)
    return source_path, process.wait()

def get_target(raw_target_name=None):
    if raw_target_name == None:
        raw_target_name = "_default"

    import cbob.project
    *subproject_names, target_name = raw_target_name.split(".")
    current_project = cbob.project.get_project(subproject_names)
    return current_project.get_target(target_name)
