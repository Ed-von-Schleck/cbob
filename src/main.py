import argparse

def _init(args):
    import src.init
    src.init.init()

def _new(args):
    import src.new
    src.new.new(args.name)

def _add(args):
    import src.add
    src.add.add(args.target, args.files)

def _list_(args):
    import src.list_
    src.list_.list_()

def _show(args):
    import src.show
    src.show.show(args.target)

def _build(args):
    import src.build
    src.build.build(args.target, args.jobs)

def _configure(args):
    import src.configure
    src.configure.configure(args.target, args.auto, args.force, args.compiler, args.linker, args.bindir)

def main():
    parser = argparse.ArgumentParser(description="cbob builds your project.", prog="cbob")
    
    subparsers = parser.add_subparsers(help="Invoke command.")

    parser_init = subparsers.add_parser("init", help="Initalize cbob for your project.")
    parser_init.set_defaults(func=_init)

    parser_new = subparsers.add_parser("new", help="Create new target.")
    parser_new.add_argument("name", help="The target's name.")
    parser_new.set_defaults(func=_new)

    parser_add = subparsers.add_parser("add", help="Add file(s) to a target.")
    parser_add.add_argument("target", help="The target to be added to.")
    parser_add.add_argument("files", metavar="file", nargs="+", help="The file(s) to be added (wildcards allowed).")
    parser_add.set_defaults(func=_add)

    parser_list = subparsers.add_parser("list", help="List targets.")
    parser_list.set_defaults(func=_list_)

    parser_show = subparsers.add_parser("show", help="Show information about a target.")
    parser_show.add_argument("target", help="The inquired target.")
    parser_show.set_defaults(func=_show)

    parser_build = subparsers.add_parser("build", help="Build one, many or all targets.")
    parser_build.add_argument("target", help="The target to build.")
    parser_build.add_argument("-j", "--jobs", nargs=1, type=int, help="The target to build.")
    parser_build.set_defaults(func=_build)

    parser_configure = subparsers.add_parser("configure", help="Set parameter(s) for a target.")
    parser_configure.add_argument("target", help="The target to configure.")
    parser_configure.add_argument("-a", "--auto", action="store_true", help="Let cbob figure things out automatically.")
    parser_configure.add_argument("-f", "--force", action="store_true", help="Force overwriting previous configuration when '--auto' is used.")
    parser_configure.add_argument("-c", "--compiler", nargs=1, help="The path to the compiler binary (e.g. '--compiler=\"/usr/bin/gcc\"').")
    parser_configure.add_argument("-l", "--linker", nargs=1, help="The path to the compiler binary (e.g. '--linker=\"/usr/bin/ld\"').")
    parser_configure.add_argument("-b", "--bindir", nargs=1, help="The path to the output directory for binaries (e.g. '--bindir=\"bin/\"').")
    parser_configure.add_argument("--cflags", nargs="*", help="The CFLAGS to use (e.g. '--cflags=\"$CFLAGS\"').")
    parser_configure.add_argument("--cxxflags", nargs="*", help="The CXXFLAGS to use (e.g. '--cxxflags=\"$CXXFLAGS\"').")
    parser_configure.add_argument("--ldflags", nargs="*", help="The LDFLAGS to use (e.g. '--ldflags=\"$LDFLAGS\"').")
    parser_configure.set_defaults(func=_configure)

    args = parser.parse_args()
    args.func(args)
