import argparse
import logging

import cbob.commands as commands

def main():
    main_parser = argparse.ArgumentParser(description="cbob builds your project.", prog="cbob")
    verbosity = main_parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", help="print more verbose output", action="store_const", const=logging.INFO, dest="verbosity", default=logging.WARNING)
    verbosity.add_argument("-q", "--quiet", help="be silent", action="store_const", const=logging.ERROR, dest="verbosity", default=logging.WARNING)
    verbosity.add_argument("-d", "--debug", help="print lots of debug output", action="store_const", const=logging.DEBUG, dest="verbosity", default=logging.WARNING)
    
    subparsers = main_parser.add_subparsers(help="Invoke command.")

    parsers = {}

    parsers["init"] = subparsers.add_parser("init", help="Initalize cbob for your project.")
    parsers["init"].set_defaults(func=commands.init)

    parsers["new"] = subparsers.add_parser("new", help="Create new target.")
    parsers["new"].add_argument("name", help="The target's name.")
    parsers["new"].set_defaults(func=commands.new)

    parsers["add"] = subparsers.add_parser("add", help="Add file(s) to a target.")
    parsers["add"].add_argument("-t", "--target", help="The target to be added to (omit to add to default target).")
    parsers["add"].add_argument("files", metavar="file", nargs="+", help="The file(s) to be added (wildcards allowed).")
    parsers["add"].set_defaults(func=commands.add)

    parsers["remove"] = subparsers.add_parser("remove", help="Remove file(s) from a target.")
    parsers["remove"].add_argument("-t", "--target", help="The target the files will be removed from (omit to remove from default target).")
    parsers["remove"].add_argument("files", metavar="file", nargs="+", help="The file(s) to be removed (wildcards allowed).")
    parsers["remove"].set_defaults(func=commands.remove)

    parsers["info"] = subparsers.add_parser("info", help="Show information about the project.")
    parsers["info"].add_argument("-a", "--all", dest="all_", action="store_true", help="Show all available information.")
    parsers["info"].add_argument("-t", "--targets", action="store_true", help="List the project's targets.")
    parsers["info"].add_argument("-s", "--subprojects", action="store_true", help="List the project's subprojects.")
    parsers["info"].set_defaults(func=commands.info)

    parsers["show"] = subparsers.add_parser("show", help="Show information about a target.")
    parsers["show"].add_argument("-t", "--target", help="The inquired target (omit to show info about default target).")
    parsers["show"].add_argument("-a", "--all", dest="all_", action="store_true", help="Show all available information about the target.")
    parsers["show"].add_argument("-s", "--sources", action="store_true", help="List the target's sources.")
    parsers["show"].add_argument("-d", "--dependencies", action="store_true", help="List the target's dependencies.")
    parsers["show"].add_argument("-p", "--plugins", action="store_true", help="List the target's plugins.")
    parsers["show"].set_defaults(func=commands.show)

    parsers["build"] = subparsers.add_parser("build", help="Build one, many or all targets.")
    parsers["build"].add_argument("-t", "--target", help="The target to build (omit to build the default target).")
    parsers["build"].add_argument("-j", "--jobs", nargs=1, type=int, help="The target to build.")
    parsers["build"].add_argument("-o", "--oneshot", action="store_true", help="Build all sources, no matter what (shortcuts dependency resolution).")
    parsers["build"].add_argument("-k", "--keep-going", dest="keep_going", action="store_true", help="Try to limb along even when compile errors happen.")
    parsers["build"].set_defaults(func=commands.build)

    parsers["subprojects"] = subparsers.add_parser("subprojects", help="Manage subprojects.")
    subprojects_subparsers = parsers["subprojects"].add_subparsers(help="Invoke command.")
    parsers["subprojects_add"] = subprojects_subparsers.add_parser("add", help="Add projects as subprojects.")
    parsers["subprojects_add"].add_argument("projects", metavar="project", nargs="+", help="The path(s) to the sub-projects.")
    parsers["subprojects_add"].set_defaults(func=commands.subprojects_add)

    parsers["subprojects_remove"] = subprojects_subparsers.add_parser("remove", help="Remove subprojects from project.")
    parsers["subprojects_remove"].add_argument("projects", metavar="project", nargs="+", help="The path(s) to the sub-projects.")
    parsers["subprojects_remove"].set_defaults(func=commands.subprojects_remove)

    parsers["dependencies"] = subparsers.add_parser("dependencies", help="Manage dependencies.")
    dependencies_subparsers = parsers["dependencies"].add_subparsers(help="Invoke command.")
    parsers["dependencies_add"] = dependencies_subparsers.add_parser("add", help="Add a dependency on other targets.")
    parsers["dependencies_add"].add_argument("-t", "--target", help="The target that requires the dependencies (omit to mean default target).")
    parsers["dependencies_add"].add_argument("dependencies", metavar="dependency", nargs="+", help="The target(s) to be added as dependencies.")
    parsers["dependencies_add"].set_defaults(func=commands.dependencies_add)

    parsers["dependencies_remove"] = dependencies_subparsers.add_parser("remove", help="Remove a dependency.")
    parsers["dependencies_remove"].add_argument("-t", "--target", help="The target to remove the dependency from (omit to mean default target).")
    parsers["dependencies_remove"].add_argument("dependencies", metavar="dependency", nargs="+", help="The dependency target(s) to be removed.")
    parsers["dependencies_remove"].set_defaults(func=commands.dependencies_remove)

    parsers["clean"] = subparsers.add_parser("clean", help="Clean out various parts.")
    parsers["clean"].add_argument("-t", "--target", help="The target to be cleaned (omit to clean default target).")
    parsers["clean"].add_argument("-a", "--all", dest="all_", action="store_true", help="Clean everything.")
    parsers["clean"].add_argument("-o", "--objects", action="store_true", help="Clean object files.")
    parsers["clean"].add_argument("-p", "--precompiled", action="store_true", help="Clean precompiled header files.")
    parsers["clean"].add_argument("-b", "--bin", dest="bin_", action="store_true", help="Clean binary files.")
    parsers["clean"].set_defaults(func=commands.clean)

    parsers["configure"] = subparsers.add_parser("configure", help="Set parameter(s) for a target.")
    parsers["configure"].add_argument("-t", "--target", help="The target to configure.")
    parsers["configure"].add_argument("-a", "--auto", action="store_true", help="Let cbob figure things out automatically.")
    parsers["configure"].add_argument("-f", "--force", action="store_true", help="Force overwriting previous configuration when '--auto' is used.")
    parsers["configure"].add_argument("-c", "--compiler", nargs=1, help="The path to the compiler binary (e.g. '--compiler=\"/usr/bin/gcc\"').")
    parsers["configure"].add_argument("-l", "--linker", nargs=1, help="The path to the compiler binary (e.g. '--linker=\"/usr/bin/ld.gold\"').")
    parsers["configure"].add_argument("-b", "--bindir", nargs=1, help="The path to the output directory for binaries (e.g. '--bindir=\"out/\"').")
    parsers["configure"].set_defaults(func=commands.configure)

    parsers["plugins"] = subparsers.add_parser("plugins", help="Manage plugins.")
    plugin_subparsers = parsers["plugins"].add_subparsers(help="Invoke command.")
    parsers["plugins_add"] = plugin_subparsers.add_parser("add", help="Register Python plugin(s) for a target.")
    parsers["plugins_add"].add_argument("-t", "--target", help="The target to for the plugin (omit to mean the default target).")
    parsers["plugins_add"].add_argument("plugins", nargs="+", help="The path to the plugin(s).")
    parsers["plugins_add"].set_defaults(func=commands.plugins_add)

    parsers["plugins_remove"] = plugin_subparsers.add_parser("remove", help="Unregister Python plugin(s) from a target.")
    parsers["plugins_remove"].add_argument("-t", "--target", help="The target to for the plugin (omit to mean the default target).")
    parsers["plugins_remove"].add_argument("plugins", nargs="+", help="The path to the plugin(s).")
    parsers["plugins_remove"].set_defaults(func=commands.plugins_remove)

    args = main_parser.parse_args()

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
