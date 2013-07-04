import logging
import argparse

from cbob.error import CbobError

def _init(args):
    import cbob.project as project
    project.init()

def _new(args):
    import cbob.project as project
    project.get_project().new_target(args.name)

def _add(args):
    import cbob.project as project
    target = project.get_project().targets[args.target]
    target.add_sources(args.files)

def _remove(args):
    import cbob.project as project
    target = project.get_project().targets[args.target]
    target.remove_sources(args.files)

def _info(args):
    import cbob.project as project
    project.get_project().info(args.all_, args.targets, args.subprojects)

def _show(args):
    import cbob.project as project
    try:
        target = project.get_project().targets[args.target]
    except KeyError:
        from cbob.error import TargetDoesntExistError
        raise TargetDoesntExistError(args.target)
    target.show(args.all_, args.sources, args.dependencies)

def _build(args):
    import cbob.project as project
    try:
        target = project.get_project().targets[args.target]
    except KeyError:
        from cbob.error import TargetDoesntExistError
        raise TargetDoesntExistError(args.target)
    target.build(args.jobs)

def _depend(args):
    import cbob.project as project
    try:
        target = project.get_project().targets[args.target]
    except KeyError:
        from cbob.error import TargetDoesntExistError
        raise TargetDoesntExistError(args.target)
    target.depend_on(args.dependencies)

def _configure(args):
    import cbob.project as project
    try:
        target = project.get_project().targets[args.target]
    except KeyError:
        from cbob.error import TargetDoesntExistError
        raise TargetDoesntExistError(args.target)
    target.configure(args.auto, args.force, args.compiler, args.linker, args.bindir)

def _subadd(args):
    import cbob.project as project
    project.get_project().add_subprojects(args.projects)

def main():
    parser = argparse.ArgumentParser(description="cbob builds your project.", prog="cbob")
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", help="print more verbose output", action="store_const", const=logging.INFO, dest="verbosity", default=logging.WARNING)
    verbosity.add_argument("-q", "--quiet", help="be silent", action="store_const", const=logging.ERROR, dest="verbosity", default=logging.WARNING)
    verbosity.add_argument("-d", "--debug", help="print lots of debug output", action="store_const", const=logging.DEBUG, dest="verbosity", default=logging.WARNING)
    
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

    parser_remove = subparsers.add_parser("remove", help="Remove file(s) from a target.")
    parser_remove.add_argument("target", help="The target the files will be removed from.")
    parser_remove.add_argument("files", metavar="file", nargs="+", help="The file(s) to be removed (wildcards allowed).")
    parser_remove.set_defaults(func=_remove)

    parser_info = subparsers.add_parser("info", help="Show information about the project.")
    parser_info.add_argument("-a", "--all", dest="all_", action="store_true", help="Show all available information.")
    parser_info.add_argument("-t", "--targets", action="store_true", help="List the project's targets.")
    parser_info.add_argument("-s", "--subprojects", action="store_true", help="List the project's subprojects.")
    parser_info.set_defaults(func=_info)

    parser_show = subparsers.add_parser("show", help="Show information about a target.")
    parser_show.add_argument("target", help="The inquired target.")
    parser_show.add_argument("-a", "--all", dest="all_", action="store_true", help="Show all available information about the target.")
    parser_show.add_argument("-s", "--sources", action="store_true", help="List the target's sources.")
    parser_show.add_argument("-d", "--dependencies", action="store_true", help="List the target's dependencies.")
    parser_show.set_defaults(func=_show)

    parser_build = subparsers.add_parser("build", help="Build one, many or all targets.")
    parser_build.add_argument("target", help="The target to build.")
    parser_build.add_argument("-j", "--jobs", nargs=1, type=int, help="The target to build.")
    parser_build.set_defaults(func=_build)

    parser_subadd = subparsers.add_parser("subadd", help="Make a target depend on other targets.")
    parser_subadd.add_argument("projects", metavar="project", nargs="+", help="A cbob project to be used as a sub-project.")
    parser_subadd.set_defaults(func=_subadd)

    parser_depend = subparsers.add_parser("depend", help="Make a target depend on other targets.")
    parser_depend.add_argument("target", help="The target that requires the dependencies.")
    parser_depend.add_argument("dependencies", metavar="dependency", nargs="+", help="The target(s) that are depended on.")
    parser_depend.set_defaults(func=_depend)

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
    #logging.basicConfig(format="%(levelname)s: %(message)s", level=args.verbosity)
    logging.basicConfig(format="%(message)s", level=args.verbosity)
    try:
        args.func(args)
    except CbobError as e:
        logging.error(e)
        exit(1)
    exit(0)
