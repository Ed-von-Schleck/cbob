import argparse
import logging

import cbob.commands as commands

def main():
    parser = argparse.ArgumentParser(description="cbob builds your project.", prog="cbob")
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", help="print more verbose output", action="store_const", const=logging.INFO, dest="verbosity", default=logging.WARNING)
    verbosity.add_argument("-q", "--quiet", help="be silent", action="store_const", const=logging.ERROR, dest="verbosity", default=logging.WARNING)
    verbosity.add_argument("-d", "--debug", help="print lots of debug output", action="store_const", const=logging.DEBUG, dest="verbosity", default=logging.WARNING)
    
    subparsers = parser.add_subparsers(help="Invoke command.")

    parser_init = subparsers.add_parser("init", help="Initalize cbob for your project.")
    parser_init.set_defaults(func=commands.init)

    parser_new = subparsers.add_parser("new", help="Create new target.")
    parser_new.add_argument("name", help="The target's name.")
    parser_new.set_defaults(func=commands.new)

    parser_add = subparsers.add_parser("add", help="Add file(s) to a target.")
    parser_add.add_argument("-t", "--target", help="The target to be added to (omit to add to default target).")
    parser_add.add_argument("files", metavar="file", nargs="+", help="The file(s) to be added (wildcards allowed).")
    parser_add.set_defaults(func=commands.add)

    parser_remove = subparsers.add_parser("remove", help="Remove file(s) from a target (omit to remove from default target).")
    parser_remove.add_argument("-t", "--target", help="The target the files will be removed from.")
    parser_remove.add_argument("files", metavar="file", nargs="+", help="The file(s) to be removed (wildcards allowed).")
    parser_remove.set_defaults(func=commands.remove)

    parser_info = subparsers.add_parser("info", help="Show information about the project.")
    parser_info.add_argument("-a", "--all", dest="all_", action="store_true", help="Show all available information.")
    parser_info.add_argument("-t", "--targets", action="store_true", help="List the project's targets.")
    parser_info.add_argument("-s", "--subprojects", action="store_true", help="List the project's subprojects.")
    parser_info.set_defaults(func=commands.info)

    parser_show = subparsers.add_parser("show", help="Show information about a target.")
    parser_show.add_argument("-t", "--target", help="The inquired target (omit to show info about default target).")
    parser_show.add_argument("-a", "--all", dest="all_", action="store_true", help="Show all available information about the target.")
    parser_show.add_argument("-s", "--sources", action="store_true", help="List the target's sources.")
    parser_show.add_argument("-d", "--dependencies", action="store_true", help="List the target's dependencies.")
    parser_show.set_defaults(func=commands.show)

    parser_build = subparsers.add_parser("build", help="Build one, many or all targets.")
    parser_build.add_argument("-t", "--target", help="The target to build (omit to build the default target).")
    parser_build.add_argument("-j", "--jobs", nargs=1, type=int, help="The target to build.")
    parser_build.add_argument("-o", "--oneshot", action="store_true", help="Build all sources, no matter what (shortcuts dependency resolution).")
    parser_build.add_argument("-k", "--keep-going", dest="keep_going", action="store_true", help="Try to limb along even when compile errors happen.")
    parser_build.set_defaults(func=commands.build)

    parser_subadd = subparsers.add_parser("subadd", help="Add projects as subprojects.")
    parser_subadd.add_argument("projects", metavar="project", nargs="+", help="Project(s) to be used as a sub-project.")
    parser_subadd.set_defaults(func=commands.subadd)

    parser_depend = subparsers.add_parser("depend", help="Make a target depend on other targets.")
    parser_depend.add_argument("-t", "--target", help="The target that requires the dependencies (omit to mean default target).")
    parser_depend.add_argument("dependencies", metavar="dependency", nargs="+", help="The target(s) that are depended on.")
    parser_depend.set_defaults(func=commands.depend)

    parser_clean = subparsers.add_parser("clean", help="Clean out various parts.")
    parser_clean.add_argument("-t", "--target", help="The target that requires the dependencies.")
    parser_clean.add_argument("-a", "--all", dest="all_", action="store_true", help="Clean everything.")
    parser_clean.add_argument("-o", "--objects", action="store_true", help="Clean object files.")
    parser_clean.add_argument("-p", "--precompiled", action="store_true", help="Clean precompiled header files.")
    parser_clean.add_argument("-b", "--bin", dest="bin_", action="store_true", help="Clean binary files.")
    parser_clean.set_defaults(func=commands.clean)

    parser_configure = subparsers.add_parser("configure", help="Set parameter(s) for a target.")
    parser_configure.add_argument("-t", "--target", help="The target to configure.")
    parser_configure.add_argument("-a", "--auto", action="store_true", help="Let cbob figure things out automatically.")
    parser_configure.add_argument("-f", "--force", action="store_true", help="Force overwriting previous configuration when '--auto' is used.")
    parser_configure.add_argument("-c", "--compiler", nargs=1, help="The path to the compiler binary (e.g. '--compiler=\"/usr/bin/gcc\"').")
    parser_configure.add_argument("-l", "--linker", nargs=1, help="The path to the compiler binary (e.g. '--linker=\"/usr/bin/ld.gold\"').")
    parser_configure.add_argument("-b", "--bindir", nargs=1, help="The path to the output directory for binaries (e.g. '--bindir=\"out/\"').")
    #parser_configure.add_argument("--flags", nargs="*", help="The CFLAGS or CXXFLAGS to use (e.g. '--flags=\"$CFLAGS\"').")
    #parser_configure.add_argument("--ldflags", nargs="*", help="The LDFLAGS to use (e.g. '--ldflags=\"$LDFLAGS\"').")
    parser_configure.set_defaults(func=commands.configure)

    parser_register = subparsers.add_parser("register", help="register a python plugin for a target.")
    parser_register.add_argument("-t", "--target", help="The target to for the plugin.")
    parser_register.add_argument("plugins", nargs="+", help="The path to the plugin.")
    parser_register.set_defaults(func=commands.register)

    args = parser.parse_args()

    logging.basicConfig(format="cbob: %(message)s", level=args.verbosity)

    from cbob.error import CbobError
    try:
        func = args.func
        argdict = args.__dict__
        del argdict["verbosity"]
        del argdict["func"]
        func(**argdict)
    except CbobError as e:
        logging.error(e)
        exit(1)
    exit(0)
