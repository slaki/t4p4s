
from __future__ import print_function

import p4c2py
import sys


p4c_path = sys.argv[1]
filename = sys.argv[2]
run_midend = False

p4ir = p4c2py.load_p4_file(filename, p4c_path, run_midend)


p4c2py.pprint_p4ir(p4ir)

print("-------------------")

print("actions", p4ir.actions)
if len(p4ir.actions) > 0:
    print("actions[0]", p4ir.actions[0])
    print("actions[0].name", p4ir.actions[0].name)
    print("actions[0].ann", p4ir.actions[0].annotations)
    if len(p4ir.actions[0].annotations) > 0:
        print("actions[0].ann[0].name", p4ir.actions[0].annotations[0].name)
    print("actions[0].par", p4ir.actions[0].parameters)
print("controls", p4ir.controls)
if len(p4ir.controls) > 0:
    print("controls[0].par", p4ir.controls[0].parameters)
    print("controls[0].tables", p4ir.controls[0].tables)
    if len(p4ir.controls[0].tables) > 0:
        print("controls.tables[0].ann", p4ir.controls[0].tables[0].annotations)
        print("controls.tables[0].par", p4ir.controls[0].tables[0].parameters)
