
from __future__ import print_function

import p4c

from itertools import takewhile
from pydoc import locate
import re


# TODO do not have a constant here, dynamically compute this
max_indent = 15


def cstr(str):
    """Turns a P4 cstring into a usual string."""
    return p4c.cstring_to_stdstring(str)


# These methods are present in almost all of the IR classes,
# most of them inherited from IR::Node, or automatically generated.
common_methods = ['apply_visitor_postorder',
                  'apply_visitor_preorder',
                  'apply_visitor_revisit',
                  'apply',
                  'clone',
                  'dump_fields',
                  'dbprint',
                  'fromJSON',
                  'getNode',
                  'getSourceInfo',
                  'node_type_name',
                  'num_children',
                  'static_type_name',
                  'toJSON',
                  'toString',
                  'traceCreation',
                  'validate',
                  'visit_children']


def xdir(node):
    """Available operations on the node, except for the common/modifying ones."""
    return [f for f in dir(node) if not f.startswith("__") and not f.startswith("add") and f not in common_methods]


def type_of(node):
    """Returns the type of the node as a string."""
    if node is None:
        return None
    return p4c.cstring_to_stdstring(node.node_type_name())


class visitor:
    """Collects data about a subtree of the IR."""

    def __init__(self, data0, pre, post=None):
        self.data = data0
        self.parents = []
        self.pre = pre
        self.post = post

    def fun_pre(self, node):
        self.parents.append(node)
        (self.data, go_on) = self.pre(self.parents, node, self.data)
        return go_on

    def fun_post(self, node):
        del self.parents[-1]
        if self.post is not None:
            self.data = self.post(self.parents, node, self.data)


def do_visit(node, data0, pre, post=None):
    """Returns the data collected from a subtree of the IR."""
    v = visitor(data0, pre, post)
    p4c.test_visitor(node, v)
    return v.data


def info(node):
    """Returns the most relevant infos about the node.
    Not properly implemented yet, almost a placeholder."""
    if type(node) == p4c.P4_IR__Type_Package:
      return cstr(node.externalName())
    if type(node) == p4c.P4_IR__P4Control:
      return cstr(node.externalName())

    return xdir(node)


def append_elem(tree, idxs, node):
    append_pos = tree
    for idx in idxs:
        if idx < len(append_pos):
            _, _, append_pos = append_pos[idx]
        else:
            append_pos.append((node, info(node), []))
            return


def op_in(parents, node, (data, indent, idxs, tree)):
    idxs[indent] += 1
    append_elem(tree, idxs[:indent+1], node)
    return ((data + 1, indent+1, idxs, tree), True)
def op_out(parents, node, (data, indent, idxs, tree)):
    idxs[indent:] = [-1] * len(idxs[indent:])
    return (data, indent-1, idxs, tree)


def find_nodes(tree, node_type):
    nodes1 = [(elem, infos, subtree)
                for elem, infos, subtree in tree if type(elem) == node_type]
    nodes2 = [node for _, _, subtree in tree for node in find_nodes(subtree, node_type)]
    return nodes1 + nodes2


# -------------------------------------
# Load the file and collect some data


class Node(object):
    def __init__(self, dict):
        self.__dict__ = dict
        self.data = {}
        self.default_funs = [
            "node_type",
            "node",
            "infos",
            "children",
            "add_elem",
            'name',
            'parent_node',
            'put',
            'data',
            'default_funs',
            'xdir'
        ]

    def __str__(self):
        return str(self.node_type) + "<" + self.name + ">" + str(self.xdir())

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, key):
        return self.data[key]

    def add_elem(self, key, value):
        """Adds a "property" to the object."""
        self.__dict__[key] = value

    def put(self, key, value):
        """Adds a queryable key-value pair to the object."""
        self.data[key] = value

    def xdir(self):
        return [d for d in dir(self) if not d.startswith("__") and d not in self.default_funs]


def ch(node_data, node_type=None):
    """Those child nodes whose type is the given one.
    If no node_type is supplied, returns the only child."""
    if type(node_data) == list:
        return [n for sub_node in node_data for n in ch(sub_node)]

    (node, infos, sub_nodes) = node_data

    if node_type is None:
        return sub_nodes
    return [sub_node for sub_node in sub_nodes if type(sub_node[0]) == node_type]


def ir_type_name(node):
    """The P4 IR type name of the node as a string."""
    return str(type(node[0]))[len("<class 'p4c.P4_IR__"):][:-2]


def grch(node):
    """Returns the grandchildren of the node in a list."""
    return [grch for _, _, ch_nodes in node for _, _, grch_nodes in ch_nodes for grch in grch_nodes]


def nodes_by_name(nodes, name):
    return [node.node for node in nodes if node.name == name]


is_tab = '\t'.__eq__


def to_python_type(name):
    if name.endswith("*"):
        name = name[:-1]
    "p4c.P4_IR__" + name
    return locate("p4c.P4_IR__" + name)


def make_python_name(name):
    if name.endswith("*"):
        name = name[:-1]
    if name.startswith("P4"):
        name = name[2:]
    return re.sub("([^_])([A-Z])", "\\1_\\2", name).lower()


def is_iterating(name):
    return name.endswith("*")


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def build_tree(lines):
    prev_depth = -1
    lines = iter(lines)
    stack = []
    retval = []

    for line in lines:
        indent = len(list(takewhile(is_tab, line)))
        if prev_depth >= indent:
            retval.append(list(stack))
        stack[indent:] = [line.strip().split(" ")]
        prev_depth = indent

    return retval


def make_node(node, parent_node=None):
    return Node({
        "node_type": ir_type_name(node),
        "node": node,
        "parent_node": parent_node,
        "infos": node[1],
        "name": cstr(node[0].toString()),
    })


def make_p4ir(ast_file, tree):
    """Converts the loaded P4 IR tree to a more convenient data structure."""
    with open(ast_file) as f:
        lines = f.readlines()

        retval = make_node(tree[0])
        for typeseq in build_tree(lines):
            currs = [(tree[0], retval)]
            for split in typeseq:
                if len(currs) == 0:
                    break

                if is_int(split[0]):
                    idx = int(split[0])
                    pyname = make_python_name(split[1])
                    pytype = to_python_type(split[1])
                elif split[0] == "zip":
                    pyname1 = make_python_name(split[1])
                    pytype1 = to_python_type(split[1])
                    pyname2 = make_python_name(split[2])
                    pytype2 = to_python_type(split[2])
                else:
                    pyname = make_python_name(split[0])
                    pytype = to_python_type(split[0])

                    if not is_iterating(split[0]) and pyname in dir(currs[0][1]):
                        nexts = [getattr(r, pyname) for _, r in currs]
                        if type(nexts[0]) == list:
                            currs = [(next.node, next) for nextlist in nexts for next in nextlist]
                        else:
                            currs = [(next.node, next) for nextlist in nexts]
                        continue

                    if is_iterating(split[0]) and pyname + "s" in dir(currs[0][1]):
                        currs = [(r2.node, r2) for (tnode, node) in currs for r2 in getattr(node, pyname + "s")]
                        continue

                    newcurrs = []
                    for tnode, node in currs:
                        founds = find_nodes([tnode], pytype)
                        elems = [make_node(found) for found in founds]

                        if is_iterating(split[0]):
                            node.add_elem(pyname + "s", elems)
                        else:
                            node.add_elem(pyname, elems)
                        newcurrs.extend(zip(founds, elems))

                    currs = newcurrs

        return retval


def pprint_p4ir(p4ir, indent="", depth=0, parent_elem=None):
    if type(p4ir) == list:
        for e in p4ir:
            pprint_p4ir(e, indent, depth, parent_elem)
    elif type(p4ir) == str:
        print(indent + "  ", "(str)", p4ir)
    else:
        print(indent, parent_elem, p4ir)
        for e in p4ir.xdir():
            pprint_p4ir(getattr(p4ir, e), indent + "    ", depth + 1, e)


def load_p4_file(filename, p4c_path, run_midend):
    p4program = p4c.load_p4_simple(filename, p4c_path, run_midend)

    if not p4program:
        return None

    init_info = (0, 0, [-1] * max_indent, [])
    node_count, _, _, tree = do_visit(p4program, init_info, op_in, op_out)

    ast_file = "p4_ir_structure.txt"
    p4ir = make_p4ir(ast_file, tree)

    return p4ir
