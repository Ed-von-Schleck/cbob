def new(name):
    import cbob.project
    *subproject_names, target_name = name.split(".")
    current_project = cbob.project.get_project(subproject_names)
    current_project.new_target(target_name)

def init():
    import cbob.project
    cbob.project.init()

def add(files, target=None):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.add_sources(files)

def remove(files, target=None):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.remove_sources(files)

def info(all_=False, targets=False, subprojects=False):
    import cbob.project
    cbob.project.get_project().info(all_, targets, subprojects)

def show(target=None, all_=False, sources=False, dependencies=False):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.show(all_, sources, dependencies)

def build(target=None, jobs=None, oneshot=None, keep_going=None):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.build(jobs, oneshot, keep_going)

def depend(target=None, dependencies=None):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.depend_on(dependencies)

def configure(target=None, auto=None, force=None, compiler=None, linker=None, bindir=None):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.configure(auto, force, compiler, linker, bindir)

def subadd(projects):
    import cbob.project
    cbob.project.get_project().add_subprojects(projects)

def clean(target=None, all_=False, objects=False, precompiled=False, bin_=False):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.clean(all_, objects, precompiled, bin_)

def register(plugins, target=None):
    import cbob.target
    current_target = cbob.target.get_target(target)
    current_target.register(plugins)


