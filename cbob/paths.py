from collections import namedtuple
import os
from os.path import join, isdir

class DirNamespace(object):
    def __init__(self, root, dirnames):
        for name, dirname in dirnames.items():
            path = join(root, dirname)
            setattr(self, name, path)
            if not isdir(path):
                os.makedirs(path)
