def new(name):
    import cbob.project
    *subproject_names, target_name = name.split(".")
    current_project = cbob.project.get_project(subproject_names)
    current_project.new_target(target_name)

def init():
    import cbob.project
    cbob.project.init()

def add(target, files):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.add_sources(files)

def remove(target, files):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.remove_sources(files)

def info(all_, targets, subprojects):
    import cbob.project
    cbob.project.get_project().info(all_, targets, subprojects)

def show(target, all_, sources, dependencies):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.show(all_, sources, dependencies)

def build(target, jobs, oneshot, keep_going):
    import cbob.target
    current_target = cbob.target.get_target(target) if target is not None else cbob.target.get_target("_default")
    current_target.build(jobs, oneshot, keep_going)

def depend(target, dependencies):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.depend_on(dependencies)

def configure(target, auto, force, compiler, linker, bindir, flags, ldflags):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.configure(auto, force, compiler, linker, bindir, flags, ldflags)

def subadd(projects):
    import cbob.project
    cbob.project.get_project().add_subprojects(projects)

def clean(target, all_, objects, precompiled, bin_):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.clean(all_, objects, precompiled, bin_)

