#!/usr/bin/env python

import clang.cindex
import sys
import os

def traverse(o, get_children, cond):
    if cond(o):
        yield o

    for value in list(o.get_children()):
        for subvalue in traverse(value, get_children, cond):
            yield subvalue

def full_name(n, separator = "::"):
    if n is None:
        return None

    retval = name(n)
    while kind(n.semantic_parent) != 'TRANSLATION_UNIT':
        # TODO unions, records could be here, too
        if kind(n.semantic_parent) in ['NAMESPACE', 'CLASS_DECL']:
            retval = name(n.semantic_parent) + separator + retval
        n = n.semantic_parent

    return retval

def kind(cursor):
    return str(cursor.kind).split(".")[1] if cursor else None

def access(cursor):
    return str(cursor.access_specifier).split(".")[1].lower()

def has_pure_virtual(cl):
    return any([m.is_pure_virtual_method() for m in methods(cl)])

def children_by_kind(cl, k):
    return [ch for ch in cl.get_children() if kind(ch) == k]

def methods(cl):
    return children_by_kind(cl, 'CXX_METHOD')

def constructors(cl):
    return children_by_kind(cl, 'CONSTRUCTOR')

def name(cursor):
    return cursor.spelling or cursor.displayname

def print_tree(translation_unit):
    print asciitree.draw_tree(translation_unit.cursor,
        lambda n: get_children(n),
        lambda n: "%s %s" % (kind(n), [attr for attr in dir(n) if not attr.startswith("_")]))

def get_operator_method_name(name):
    return name[len("operator"):]

def param_string(param):
    """Some classes don't seem to get the IR:: namespace prefix that they're supposed to.
    This function manually fixes their name."""
    changes = {
        "IndexedVector": "IR::IndexedVector",
        "Vector": "IR::Vector",
        "NameMap": "IR::NameMap",
    }
    for changed in changes:
        modified = param.replace(changed, changes[changed])
        if modified != param:
            param = modified
            break
    return param.replace("IR::IR", "IR")

def is_same_method(m, m2):
    return  all([   name(m) == name(m2),
                    m.is_const_method() == m2.is_const_method(),
                    m.is_static_method() == m2.is_static_method(),
                    m.result_type.get_canonical().spelling == m2.result_type.get_canonical().spelling,
                    [arg.type.get_canonical() for arg in m.get_arguments()] == [arg.type.get_canonical() for arg in m2.get_arguments()]
                ])

def base_class_has_same_method(all_base_classes, m):
    if all_base_classes == []:
        return False
    basecl = all_base_classes[-1]
    return any([True for m2 in methods(basecl) if is_same_method(m, m2)])


if len(sys.argv) < 2:
    print "Usage: {} p4c_dir [output_file]".format(sys.argv[0])
    sys.exit()

p4c_path = sys.argv[1]
output_file = sys.argv[2] if len(sys.argv) > 2 else "p4c.cpp.boosted"

paths = [(p4c_path, "ir", "ir.h")]
classes = []
for path in paths:
    hdr_file = os.path.join(*path)
    index = clang.cindex.Index(clang.cindex.conf.lib.clang_createIndex(False, True))
    translation_unit = index.parse(hdr_file, ['-x', 'c++-header', "-std=c++11", "-I", "/usr/include", "-I", "/usr/lib/llvm-3.8/lib/clang/3.8.0/include/", "-I", p4c_path])
    classes.extend(list(traverse(translation_unit.cursor, lambda n: get_children(n), lambda n: kind(n) == 'CLASS_DECL' and n.is_definition())))

# TODO currently running generator only on classes in the IR namespace
# used_classes = [cl for cl in classes if full_name(cl).startswith("IR::")]
used_classes = [cl for cl in classes if full_name(cl).startswith("IR::") or 'Vector' in full_name(cl)]
# used_classes = [cl for cl in classes if not full_name(cl).startswith("std::") and '::' in full_name(cl)]
# used_classes = classes

with open(output_file, 'w') as f:
    for cl in used_classes:
        modname = "P4_" + full_name(cl, '__')
        # base_classes = ", ".join([full_name(bsp.get_definition()) for bsp in children_by_kind(cl, 'CXX_BASE_SPECIFIER') if full_name(bsp.get_definition()) in [full_name(cl2) for cl2 in used_classes]])
        all_base_classes = [bsp.get_definition() for bsp in children_by_kind(cl, 'CXX_BASE_SPECIFIER') if full_name(bsp.get_definition()) in [full_name(cl2) for cl2 in used_classes]]
        # TODO we could use all of them, not just the last one
        #      note: base class may not be listed if a related base class is already present
        if all_base_classes == []:
            base_class_name = ""
        else:
            base_class_name = full_name(all_base_classes[-1])

        # TODO could be relaxed, probably non-abstract classes don't have to have this restriction
        copyable = ", boost::noncopyable "

        f.write("    class_< {} {}, bases<{}> >(\"{}\", no_init)\n".format(full_name(cl), copyable, base_class_name, modname))

        if has_pure_virtual(cl):
            f.write("        // class {} has pure virtual methods, no constructors generated\n".format(full_name(cl)))
        else:
            for con in constructors(cl):
                params = [param_string(arg.type.get_canonical().spelling) for arg in con.get_arguments()]
                f.write("        // skippint init because we do not need to create objects: .def(init< {} >())\n".format(", ".join(params)))
                # f.write("        .def(init< {} >())\n".format(", ".join(params)))

        for m in methods(cl):
            if access(m) != "public":
                continue

            # we probably won't need iterator support
            # TODO "iterator" is actually a typedef for "const IR::Node *const *" in IR::VectorBase; should handle it in a more general way?
            if m.result_type.spelling == "iterator":
                f.write("        // skipping method {} because it returns an iterator\n".format(name(m)))
                continue

            param_types = [arg.type.get_canonical() for arg in m.get_arguments()]
            param_type_txts = [ptype.spelling for ptype in param_types]

            # currently we don't support rvalue-references
            if any([kind(ptype) == "RVALUEREFERENCE" for ptype in param_types]):
                continue

            sig_const = " const" if m.is_const_method() else ""
            sig_ptr   = "{}::*".format(full_name(cl)) if not m.is_static_method() else "*"
            signature = "{} ({})({}){}".format(m.result_type.get_canonical().spelling, sig_ptr, ", ".join(param_type_txts), sig_const)

            if name(m).startswith("operator"):
                # TODO doesn't always operate on the same types
                # f.write("        .def(self {} self)\n".format(get_operator_method_name(name(m))))
                continue

            # these methods are not useful for us, so we skip generating them
            # should they become useful later on, removing them from this list re-enables them
            skip_prefixes = ["add", "apply_visitor", "clone", "dbprint", "dump_fields", "fromJSON", "getNode", "static_type_name", "toJSON", "validate", "visit_children"]

            if any([name(m).startswith(prefix) for prefix in skip_prefixes]):
                f.write("        // skipping method by name: \"{}\", ({})&{})\n".format(name(m), signature, full_name(m)))
                continue
            if base_class_has_same_method(all_base_classes, m):
                f.write("        // skipping method already in base class: \"{}\", ({})&{})\n".format(name(m), signature, full_name(m)))
            # pointer results, except for "const char *" will be passed as internal C++ pointers
            elif kind(m.result_type.get_canonical()) == 'POINTER' and m.result_type.get_canonical().spelling != "const char *":
                f.write("        .def(\"{}\", ({})&{}, return_internal_reference<>())\n".format(name(m), signature, full_name(m)))
            else:
                f.write("        .def(\"{}\", ({})&{})\n".format(name(m), signature, full_name(m)))

        f.write("    ;\n")
        f.write("\n")
