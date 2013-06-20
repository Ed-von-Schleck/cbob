import src.pathhelpers as pathhelpers

def build(target_name):
    target_dir = pathhelpers.get_target_dir(target_name)
    sources_dir = pathhelpers.get_sources_dir(target_name)
