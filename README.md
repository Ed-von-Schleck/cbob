`cbob` builds your C/C++ projects. It does automatic dependency resolution (well, with the help of gcc, but still) of your source files. Contrary to most build tools out there, it does *not* need configuration files - you use it solely over the CLI (it might grow a GUI at some time). `cbob` tries to do as little magic as possible, prefers explicicity over implicity and ease of use over being the most generic tool out there.

`cbob` is far from complete at the moment, but here's what works:

Usage
-----

### Help ###

Do
```bash
cbob --help
```
to get a list overview over the possible commands. To get help for a specific command, do
```bash
cbob <command> --help
```

### Commands ###

#### Init cbob ####

In your project's root directory, do
```bash
cbob init
```
to initialize `cbob` for your project.

#### Create a new target ####

Every project needs at least one target to be defined. The name of the target is also the name of the resulting binary. To create a target, do
```bash
cbob new <target-name>
```

#### Adding a file to a target ####

Building a target means building all source files that have been added to it. You can use wildcards like `src/*.c`, but it will *not* magically add files you add to `src/` after that (it does not track the directory, only files). `cbob` does not accept non-standard file endings. There's no need to add header files or other dependencies. To add one or more files, do
```bash
cbob add <target-name> <path-to-source-file> [<path-to-other-source-file> ...]
```

#### Configuring a target ####

At the very least, a compiler need to be chosen. There is more, though: Do `cbob configure --help` to get a list of all configuration options. To try and let cbob figure it all out for you, do
```bash
cbob configure --auto
```

#### Building a target ####

Simply do
```bash
cbob build <target-name>
```
and you will end up with a binary in the directory you configured for your output (if you chose to auto-configure it's either `bin/` if it's there or the project's root). It will automatically use as many processes as there are cpus (or you can specify the number manually with `-j`/`--jobs`).

Planned Features
----------------

* Target dependencies: Require other targets to be build and up-to-date (e.g. think of an `all` target that depends on all other targets).
* Runners: Run code (shell files or binaries) before or after compiling (like for checks and tests).
* Hash-based dependency-tracking: In addition to looking at `mtime`s of files, `cbob` will look at the SHA{256,512} hash value of a (preprocessed) source to determine if it has changed, or maybe changed back to a previously compiled object file that is still in the object file cache.
* Options: Make it easy to define `--enable-foo` style configuration options.
* Libtool support: Use libtool to make building libraries easier.

Maybe-Features
--------------

* Target overlays: A target that just overlays some option (e.g. exchanging `-Og` with `-O2` in the CFLAGS), but transparently follows it's parent target's changes (e.g. think of a `release` overlay for the `development` target). So far, I haven't had an idea how to implement this elegantly.
* Support for similar languages, e.g. D or Rust
* Sub-projects: Let `cbob` handle projects in subdirectories (think of git submodules, and stuff like pre-checks as `cbob`-projects, hosted on github, as easily re-usable recipies).

Non-Features
------------

Things that are out of scope (though you may try to convince me otherwise):
* Support for every language out there (but maybe support for doing, say, Python-modules written in C).
* Support for system-wide installation (though I like `cbob` to be able to play nice with make/autotools).

How it works
------------

Just look in your `.cbob` directory. Every target is a subdirectory of `.cbob/targets`. Every source file is a symlink in its `sources` subdirectory. The source's file path relative to the project root is mangled (`/` replaced with `_`) so that it is a flat list. Similarly, the configured compiler is just a symlink, and so on.

When `cbob` build a target, it first assembles a list of all source files for that target (reading the symlinks in the `source` subdirectory). Then it creates a directed acyclical graph (DAG) from the dependencies (well, hopefully acyclical - it will fail noisily if it isn't). The nodes are then partially ordered via a topological sort, and iterated over from the end points first. For every node, it checks if it's a source file (and not a header), and if it is, `cbob` marks it as *dirty* if it's `mtime` is newer than the corresponding object file. Then, `cbob` will update the `mtime` of nodes directly depending on our node in question with `max(node, child_node)`.

That's it. The dirty nodes will be recompiled, and if there is at least on dirty node, the linking step will be performed.

Feedback
--------

As you obviously just stumbled over this very new piece of software, I am very much interested in your opinion about it (try it - it ist usable? How is it better/worse than other tools? Is it fast enough? Is it documented enough? Can it do enough? Is it cool enough?). Just open an issue on github and drop a line or two there.

Better yet, contribute to it. It is written in Python (though in a style that lets me transition to C; I haven't made up my mind about it yet), so it's fun. I'll gladly take pull requests.
