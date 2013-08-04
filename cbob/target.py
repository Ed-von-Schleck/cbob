from collections import namedtuple
from contextlib import contextmanager
import logging
from functools import partial
import os
from os.path import basename, join, islink, normpath, isdir, isfile, expandvars, split, splitext
import subprocess

from cbob.helpers import read_symlink, make_rel_symlink, print_information, log_summary
from cbob.definitions import SOURCE_FILE_EXTENSIONS, HOOKS, SYNONYMS_FOR_OFF, SYNONYMS_FOR_ON
from cbob.node import SourceNode, HeaderNode
from cbob.paths import DirNamespace

class Target(object):
    def __init__(self, path, project):
        self.path = path
        self.name = basename(path)
        self.project = project
        self._sources = None
        self._dependencies = None
        self._compiler = None
        self._bin_dir = None
        self._language = None
        self._plugins = None
        self._options = None
        self.dirs = DirNamespace(path, {
            "sources": "sources",
            "dependencies": "dependencies",
            "options": "options",
            "plugins": "plugins",
            "objects": ".objects",
            "precompiled_headers": ".precompiled_headers"})

    @property
    def sources(self):
        if self._sources is None:
            self._sources = [read_symlink(name, self.dirs.sources) for name in os.listdir(self.dirs.sources)]
        return self._sources

    @property
    def dependencies(self):
        if self._dependencies is None:
            self._dependencies = {raw_dep_name: get_target(raw_dep_name) for raw_dep_name in os.listdir(self.dirs.dependencies)}
        return self._dependencies

    @property
    def compiler(self):
        if self._compiler is None:
            with self.assume_configured():
                self._compiler = os.readlink(join(self.path, "compiler"))
        return self._compiler

    @property
    def bin_dir(self):
        if self._bin_dir is None:
            with self.assume_configured():
                self._bin_dir= os.readlink(join(self.path, "bin_dir"))
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
            plugins_dir = self.dirs.plugins
            self._plugins = {}
            for filename in os.listdir(plugins_dir):
                abs_filename = read_symlink(filename, plugins_dir)
                path, filename = split(abs_filename)
                name, ext = splitext(filename)
                fp, fn, desc = imp.find_module(name, [path])
                plugin_module = imp.load_module(name, fp, fn, desc)
                for hook, func in vars(plugin_module).items():
                    if hook in HOOKS:
                        if not hook in self._plugins:
                            self._plugins[hook] = {}
                        self._plugins[hook][abs_filename] = func
        return self._plugins

    @property
    def options(self):
        if self._options == None:
            self._options = {}
            for name in os.listdir(self.dirs.options):
                self._options[name] = {}
                this_option_dir = join(self.dirs.options, name)
                for choice in os.listdir(this_option_dir):
                    with open(join(this_option_dir, choice), "r") as choice_f:
                        self._options[name][choice] = choice_f.readlines()

        return self._options

    def _source_filetype_check(self, file_name, abs_file_path, symlink_path):
        if not splitext(file_name)[1] in SOURCE_FILE_EXTENSIONS:
            logging.warning("'{}' does not seem to be a C/C++ source file (ending is not one of {}).".format(file_name, ", ".join(SOURCE_FILE_EXTENSIONS)))
            return False
        return True


    def add_sources(self, source_globs):
        self.run_plugins("pre_add")
        self._add_something_from_globs("sources", source_globs, "file", [self._source_filetype_check])
        self._sources = None
        self.run_plugins("post_add")
    
    def remove_sources(self, source_globs):
        self._remove_something_from_globs("sources", source_globs, "file")
        self._sources = None

    def list_(self):
        print_information("Sources", self.sources)

    def dependencies_add(self, dependencies):
        added_deps = []
        for raw_dep in dependencies:
            symlink_path = join(self.dirs.dependencies, raw_dep)
            if islink(symlink_path):
                logging.info("Target '{}' is already a dependency of target '{}'.".format(raw_dep, self.name))
                continue
            from cbob.error import TargetDoesntExistError
            try:
                dep_target = get_target(raw_dep)
            except TargetDoesntExistError as e:
                logging.warning("Target '{}' is not really a target.".format(raw_dep))
                continue
            make_rel_symlink(dep_target.path, symlink_path)
            added_deps.append(raw_dep)
        log_summary(added_deps, "dependency", added=True, target_name=self.name, plural="dependencies")
        self._dependencies = None

    def dependencies_remove(self, dependencies):
        removed_deps = []
        for raw_dep in dependencies:
            symlink_path = join(self.dirs.dependencies, raw_dep)
            try:
                os.unlink(symlink_path)
            except OSError:
                logging.warning("Target '{}' is not a dependency of target '{}'.".format(raw_dep, self.name))
                continue
            removed_deps.append(raw_dep)

        log_summary(removed_deps, "dependency", added=False, target_name=self.name, plural="dependencies")
        self._dependencies = None

    def dependencies_list(self):
        print_information("Dependencies", self.dependencies)

    def plugins_add(self, plugin_globs):
        self._add_something_from_globs("plugins", plugin_globs, "plugin")
        self._plugins = None
        
    def plugins_remove(self, plugin_globs):
        self._remove_something_from_globs("plugins", plugin_globs, "plugin")
        self._plugins = None

    def plugins_list(self):
        print("Plugins:")
        empty = True
        for hookname, funcs in self.plugins.items():
            if funcs:
                empty = False
                print(" ", hookname + ":")
                for path in funcs.keys():
                    print("   ", path)
        if empty:
            print("  (none)")

    def options_new(self, name, choices):
        if choices == None:
            choices = ("on", "off")
        new_option_dir = join(self.dirs.options, name)
        logging.debug("creating option '{}' in directory '{}'".format(name, new_option_dir))
        try:
            os.mkdir(new_option_dir)
        except OSError as e:
            from cbob.error import CbobError
            raise CbobError("Option '{}' for target '{}' already exists.".format(name, self.name)) from e
        for choice in choices:
            if choice in SYNONYMS_FOR_ON:
                choice = "on"
            elif choice in SYNONYMS_FOR_OFF:
                choice = "off"
            open(join(new_option_dir, choice), "a").close()

    def options_edit(self, option, choice, editor):
        option_dir = join(self.dirs.options, option)
        if not isdir(option_dir):
            from cbob.error import OptionDoesntExistError 
            raise OptionDoesntExistError(self.name, option)
        choice_filename = join(option_dir, choice)
        if not isfile(choice_filename):
            from cbob.error import ChoiceDoesntExistError
            raise ChoiceDoesntExistError(self.name, option, choice)
        if editor is None:
            editor = expandvars("$EDITOR")
            if editor == "$EDITOR":
                editor = "/usr/bin/vi"
        import tempfile
        import shutil
        import sys
        with tempfile.NamedTemporaryFile(encoding=sys.stdout.encoding, mode="r+") as tmp_file, \
                open(choice_filename, "r", encoding=sys.stdout.encoding) as choice_file:
            tmp_file.write("# Flags for choice '{}' of option '{}' of target '{}'.\n".format(choice, option, self.name))
            tmp_file.write("# Add compiler arguments (like '-g' or '-O2'). Use one line per argument.\n")
            tmp_file.write("# The order of the arguments is being preserved.\n")
            tmp_file.write("# Lines starting with '#' are ignored.\n\n")
            shutil.copyfileobj(choice_file, tmp_file)
            tmp_file.flush()
            if subprocess.call((editor, tmp_file.name)) != 0:
                from cbob.error import CbobError
                raise CbobError("Cancelled editing of option '{}'.".format(option))
            tmp_file.flush()
            tmp_file.seek(0)
            new_flags = [line.strip() for line in tmp_file.readlines() if line and not line.startswith("#")]
        with open(choice_filename, "w", encoding=sys.stdout.encoding) as choice_file:
            choice_file.writelines(new_flags)


    def options_info(self):
        print_information("Options", self.options)

    def options_list(self, option):
        print_information("Option '{}'".format(option), self.options[option])

    def build(self, jobs, oneshot, keep_going):
        for dep_name, dep_target in self.dependencies.items():
            logging.info("Building dependency '{}'.".format(dep_name))
            dep_target.build(jobs, oneshot, keep_going)
            logging.info("Done building dependency '{}'".format(dep_name))
        self._build_self(jobs, oneshot, keep_going)

    def _build_self(self, jobs, oneshot, keep_going):
        from multiprocessing.pool import ThreadPool
        self.run_plugins("pre_build")
        # Bail out if there are no sources -
        # there is no need for a virtual target to be fully configured.
        sources = self.sources
        if not sources:
            logging.info("No sources - nothing to do.")
            return
        
        if self.compiler is None or self.bin_dir is None:
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
            cmd = [self.compiler, "-o", bin_path] + object_file_names
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

    def _calculate_dependencies(self, oneshot, pool):
        from itertools import zip_longest
        source_node_index = {}
        header_node_index = {}
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

    def configure(self, auto, force, compiler, bin_dir):
        #if not None in {compiler, bin_dir}:
        #    auto = True
        if compiler is not None:
            os.symlink(compiler, join(self.path, "compiler"))
            self._compiler = None
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
            if bin_dir is None:
                bin_dir_symlink = self._check_prepare_symlink("bin_dir", "binary output directory", force)
                if bin_dir_symlink is not None:
                    assumed_bindir = join(self.project.root_path, "bin")
                    bindir_auto = assumed_bindir if isdir(assumed_bindir) else self.project.root_path
                    os.symlink(bindir_auto, bin_dir_symlink)
                    self._bin_dir = None
        logging.info("compiler: '{}', "
                     "binary output directory: '{}'".format(self.compiler, self.bin_dir))

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

    def _clean_dir(self, dir_path):
        for file_name in os.listdir(dir_path):
            file_path = join(dir_path, file_name)
            os.remove(file_path)
            logging.debug("removed file '{}'".format(file_name))


    def clean(self, all_, object_files, pch_files, bin_file):
        if all_ or object_files:
            self._clean_dir(self.dirs.objects)
            logging.info("cleaned object files")
        if all_ or pch_files:
            self._clean_dir(self.dirs.precompiled_headers)
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
        if hookname in self.plugins:
            for func in self.plugins[hookname].values():
                logging.debug("running plugin function '{}'".format(func))
                func(self)

    def _remove_something_from_globs(self, dirname, globs, thing):
        self.project._remove_something_from_globs(join(self.path, dirname), globs, thing, self.name)

    def _add_something_from_globs(self, dirname, globs, thing, checks=None):
        self.project._add_something_from_globs(join(self.path, dirname), globs, thing, checks=checks, target_name=self.name)

    @contextmanager
    def assume_configured(self):
        try:
            yield
        except OSError as e:
            from cbob.error import NotConfiguredError
            raise NotConfiguredError(self.name) from e

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
    deps = [(len(dots), normpath(rest)) for (dots, sep, rest) in raw_deps]
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


