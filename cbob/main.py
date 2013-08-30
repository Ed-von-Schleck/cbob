import argparse
import logging

import cbob.commands as commands

def main():
    main_parser = argparse.ArgumentParser(description="cbob builds your project.", prog="cbob")
    verbosity = main_parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", help="print more verbose output", action="store_const", const=logging.INFO, dest="verbosity", default=logging.WARNING)
    verbosity.add_argument("-q", "--quiet", help="be silent", action="store_const", const=logging.ERROR, dest="verbosity", default=logging.WARNING)
    verbosity.add_argument("--debug", help="print lots of debug output", action="store_const", const=logging.DEBUG, dest="verbosity", default=logging.WARNING)
    
    subparsers = main_parser.add_subparsers(help="Invoke command.")

    parsers = {}

    parsers["init"] = subparsers.add_parser("init", help="Initalize cbob for your project.")
    parsers["init"].set_defaults(func=commands.init)

    parsers["new"] = subparsers.add_parser("new", help="Create new target.")
    parsers["new"].add_argument("name", help="The target's name.")
    parsers["new"].set_defaults(func=commands.new)

    parsers["delete"] = subparsers.add_parser("delete", help="Delete a target.")
    parsers["delete"].add_argument("name", help="The target's name.")
    parsers["delete"].set_defaults(func=commands.delete)

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

    parsers["list"] = subparsers.add_parser("list", help="List sources of target.")
    parsers["list"].add_argument("-t", "--target", help="The inquired target (omit to show info about default target).")
    parsers["list"].set_defaults(func=commands.list_)

    parsers["build"] = subparsers.add_parser("build", help="Build one, many or all targets.")
    parsers["build"].add_argument("-t", "--target", help="The target to build (omit to build the default target).")
    parsers["build"].add_argument("-j", "--jobs", type=int, help="The target to build.")
    parsers["build"].add_argument("-o", "--oneshot", action="store_true", help="Build all sources, no matter what (shortcuts dependency resolution).")
    parsers["build"].add_argument("-k", "--keep-going", dest="keep_going", action="store_true", help="Try to limb along even when compile errors happen.")
    parsers["build"].set_defaults(func=commands.build)

    parsers["clean"] = subparsers.add_parser("clean", help="Clean out various parts.")
    parsers["clean"].add_argument("-t", "--target", help="The target to be cleaned (omit to clean default target).")
    parsers["clean"].add_argument("-a", "--all", dest="all_", action="store_true", help="Clean everything.")
    parsers["clean"].add_argument("-o", "--objects", action="store_true", help="Clean object files.")
    parsers["clean"].add_argument("-p", "--precompiled", action="store_true", help="Clean precompiled header files.")
    parsers["clean"].add_argument("-b", "--bin", dest="bin_", action="store_true", help="Clean binary files.")
    parsers["clean"].set_defaults(func=commands.clean)

    parsers["configure"] = subparsers.add_parser("configure", help="Set parameter(s) for a target.")
    parsers["configure"].add_argument("-t", "--target", help="The target to configure.")
    parsers["configure"].add_argument("-a", "--auto", action="store_true", help="Let cbob figure things out automatically (enabled if no other argument is given).")
    parsers["configure"].add_argument("-f", "--force", action="store_true", help="Force overwriting previous configuration when '--auto' is used.")
    parsers["configure"].add_argument("-c", "--compiler", nargs=1, help="The path to the compiler binary (e.g. '--compiler=\"/usr/bin/gcc\"').")
    parsers["configure"].add_argument("-b", "--bindir", nargs=1, help="The path to the output directory for binaries (e.g. '--bindir=\"out/\"').")
    parsers["configure"].set_defaults(func=commands.configure)

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

    parsers["dependencies_list"] = dependencies_subparsers.add_parser("list", help="List dependencies.")
    parsers["dependencies_list"].add_argument("-t", "--target", help="The target to list the dependencies of (omit to mean default target).")
    parsers["dependencies_list"].set_defaults(func=commands.dependencies_list)

    parsers["plugins"] = subparsers.add_parser("plugins", help="Manage plugins.")
    plugin_subparsers = parsers["plugins"].add_subparsers(help="Invoke command.")
    parsers["plugins_add"] = plugin_subparsers.add_parser("add", help="Register Python plugin(s) for a target.")
    parsers["plugins_add"].add_argument("-t", "--target", help="The target for the plugin (omit to mean the default target).")
    parsers["plugins_add"].add_argument("plugins", nargs="+", help="The path to the plugin(s).")
    parsers["plugins_add"].set_defaults(func=commands.plugins_add)

    parsers["plugins_remove"] = plugin_subparsers.add_parser("remove", help="Unregister Python plugin(s) from a target.")
    parsers["plugins_remove"].add_argument("-t", "--target", help="The target for the plugin (omit to mean the default target).")
    parsers["plugins_remove"].add_argument("plugins", nargs="+", help="The path to the plugin(s).")
    parsers["plugins_remove"].set_defaults(func=commands.plugins_remove)

    parsers["plugins_list"] = plugin_subparsers.add_parser("list", help="List Python plugins of a target.")
    parsers["plugins_list"].add_argument("-t", "--target", help="The target of the plugins (omit to mean the default target).")
    parsers["plugins_list"].set_defaults(func=commands.plugins_list)

    parsers["options"] = subparsers.add_parser("options", help="Manage options.")
    options_subparsers = parsers["options"].add_subparsers(help="Invoke command.")
    parsers["options_new"] = options_subparsers.add_parser("new", help="Create a new configuration option for a target.")
    parsers["options_new"].add_argument("-t", "--target", help="The target the option belongs to (omit to mean the default target).")
    parsers["options_new"].add_argument("-c", "--choices", nargs="+", help="Possible choices for that option (default: 'on off').")
    parsers["options_new"].add_argument("name", help="The name of the option.")
    parsers["options_new"].set_defaults(func=commands.options_new)

    parsers["options_edit"] = options_subparsers.add_parser("edit", help="Edit the flags of a configuration option.")
    parsers["options_edit"].add_argument("-t", "--target", help="The target the option belongs to (omit to mean the default target).")
    parsers["options_edit"].add_argument("-c", "--choice", default="on", help="The choice to edit (e.g. 'off', default: 'on'.")
    parsers["options_edit"].add_argument("-e", "--editor", help="The editor to use (default: $EDITOR, fallback: '/usr/bin/vi').")
    parsers["options_edit"].add_argument("-a", "--add", default="ask", choices=("yes", "no", "ask"), help="Create the choice if it doesn't exist (default: 'ask').")
    parsers["options_edit"].add_argument("option", help="The name of the option to edit.")
    parsers["options_edit"].set_defaults(func=commands.options_edit)

    parsers["options_info"] = options_subparsers.add_parser("info", help="Print information about the options of a target.")
    parsers["options_info"].add_argument("-t", "--target", help="The target that is inquired about (omit to mean the default target).")
    parsers["options_info"].set_defaults(func=commands.options_info)

    parsers["options_list"] = options_subparsers.add_parser("list", help="Print information about a specific option of a target.")
    parsers["options_list"].add_argument("-t", "--target", help="The target that is inquired about (omit to mean the default target).")
    parsers["options_list"].add_argument("option", help="The option that is inquired about.")
    parsers["options_list"].set_defaults(func=commands.options_list)

    args, extra = main_parser.parse_known_args()

    logging.basicConfig(format="cbob: %(message)s")
    logger = logging.getLogger()
    logger.setLevel(args.verbosity)


    from cbob.error import CbobError
    try:
        func = args.func
        argdict = vars(args)
        del argdict["verbosity"]
        del argdict["func"]
        if "args" in argdict:
            extra += argdict["args"]
            del argdict["args"]
        if extra:
            func(args=extra, **argdict)
        else:
            func(**argdict)
    except CbobError as e:
        logging.error(e)
        exit(1)
    exit(0)
