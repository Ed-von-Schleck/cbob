from functools import partial
import os

from cbob.node import SourceNode, HeaderNode

class DepGraph(object):
    def __init__(self, target):
        self.target = target

        source_nodes = []
        header_node_index = {}
        # This is somewhat straight-forward if you have ever written a stream-parser (like SAX) in that we maintain a stack
        # of where we currently sit in the tree.
        # It adds a twist, though, in that we save references to processed nodes in a set. It may be a bit unintuitive that
        # we only skip a node if it was in another node's dependencies - but note how, when we process a node, we don't add
        # an edge to that very node, but to the node one layer *down* in the stack. Think about it for a while, then it makes
        # sense.
        processed_nodes = set()

        get_dep_info = partial(_get_dep_info, gcc_path=target.project.gcc_path)
        for file_path, deps in target.worker_pool.imap_unordered(get_dep_info, target.sources):
            node = SourceNode(file_path, self)
            source_nodes.append(node)
            parent_nodes_stack = [node]

            includes = []

            for current_depth, dep_path in deps:
                includes.append("#include \"" + dep_path + "\"\n")
                node.add_include(dep_path)
                if dep_path in header_node_index:
                    current_node = header_node_index[dep_path]
                    if current_node in processed_nodes:
                        continue
                    processed_nodes |= current_node.dependencies
                else:
                    current_node = HeaderNode(dep_path)
                    header_node_index[dep_path] = current_node

                parent_nodes_stack[:] = parent_nodes_stack[:current_depth]
                parent_nodes_stack[-1].dependencies.add(current_node)
                parent_nodes_stack.append(current_node)

            node.finalize()
        self.roots = source_nodes

def _get_dep_info(file_path, gcc_path):
    import subprocess
    from os.path import normpath
    # The options used:
    # * -H: prints the dotted header information
    # * -w: suppressed warnings
    # * -E: makes GCC stop after the preprocessing (no compilation)
    # * -P: removes comments
    cmd = (gcc_path, "-H", "-w", "-E", "-P", file_path)
    # For some reason gcc outputs the header information over `stderr`.
    # Not that this is documented anywhere ...
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
        out, err = process.communicate()
    # The output looks like
    #     . inc1.h
    #     .. inc1inc1.h
    #     . inc2.h
    # etc., with inc1inc1.h being included by inc1.h. In other words, the number of dots
    # indicates the level of nesting. Also, there are lots of lines of no interest to us.
    # Let's ignore them.
    raw_deps = (line.partition(" ") for line in err.split("\n") if line and line[0] == ".")
    deps = [(len(dots), normpath(rest)) for (dots, sep, rest) in raw_deps]
    return file_path, deps
