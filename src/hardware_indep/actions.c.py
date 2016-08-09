# Copyright 2016 Eotvos Lorand University, Budapest, Hungary
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from p4_hlir.hlir.p4_headers import p4_field, p4_field_list, p4_header_keywords
from p4_hlir.hlir.p4_imperatives import p4_signature_ref
from utils.misc import addError, addWarning 
from utils.hlir import *
import math

#[ #include "dpdk_lib.h"
#[ #include "actions.h"
#[ #include <unistd.h>
#[ #include <arpa/inet.h>
#[
#[ extern backend bg;
#[

# =============================================================================
# Helpers for field access and update
# (read/write the cached/pre-parsed value where possible)

# TODO now that these abstractions have been made, we might decide to
#   get rid of _AUTO versions of macros and implement the branching here

def modify_int32_int32(f):
    generated_code = ""
    if parsed_field(hlir, f):
        #[ pd->fields.${fld_id(f)} = value32;
    else:
        #[ MODIFY_INT32_INT32_AUTO(pd, ${fld_id(f)}, value32)
    return generated_code

def extract_int32(f, var):
    generated_code = ""
    if parsed_field(hlir, f):
        #[ res32 = pd->fields.${fld_id(f)};
    else:
        #[ EXTRACT_INT32_AUTO(pd, ${fld_id(f)}, ${var})
    return generated_code

# =============================================================================
# Helpers for saturating in add_to_field

def max_value(bitwidth, signed):
    if signed:
        return long(math.pow(2,bitwidth-1)) - 1
    else:
        return long(math.pow(2,bitwidth)) - 1

def min_value(bitwidth, signed):
    if signed:
        return -long(math.pow(2,bitwidth-1)) + 1
    else:
        return 0

# dst += src;
def add_with_saturating(dst, src, bitwidth, signed):
    generated_code = ""
    upper = max_value(bitwidth, signed)
    lower = min_value(bitwidth, signed)
    #[ if (${upper} - ${dst} < ${src}) ${dst} = ${upper};
    #[ else if (${lower} - ${dst} > ${src}) ${dst} = ${lower};
    #[ else ${dst} += ${src};
    return generated_code

# =============================================================================
# MODIFY_FIELD

def modify_field(fun, call):
    generated_code = ""
    args = call[1]
    dst = args[0]
    src = args[1]
    # mask = args[2]
    if not isinstance(dst, p4_field):
        addError("generating modify_field", "We do not allow changing an R-REF yet")
    if isinstance(src, int):
        #[ value32 = ${src};
        if dst.width <= 32:
            #[ ${ modify_int32_int32(dst) }
        else:
            if dst.width % 8 == 0 and dst.offset % 8 == 0:
                #[ MODIFY_BYTEBUF_INT32(pd, ${fld_id(dst)}, value32) //TODO: This macro is not implemented
            else:
                addError("generating modify_field", "Improper bytebufs cannot be modified yet.")
    elif isinstance(src, p4_field):
        if dst.width <= 32 and src.width <= 32:
            if src.instance.metadata == dst.instance.metadata:
                #[ EXTRACT_INT32_BITS(pd, ${fld_id(src)}, value32)
                #[ MODIFY_INT32_INT32_BITS(pd, ${fld_id(dst)}, value32)
            else:
                #[ ${ extract_int32(src, 'value32') }
                #[ ${ modify_int32_int32(dst) }
        elif src.width != dst.width:
            addError("generating modify_field", "bytebuf field-to-field of different widths is not supported yet")
        else:
            if dst.width % 8 == 0 and dst.offset % 8 == 0 and src.width % 8 == 0 and src.offset % 8 == 0 and src.instance.metadata == dst.instance.metadata:
                #[ MODIFY_BYTEBUF_BYTEBUF(pd, ${fld_id(dst)}, FIELD_BYTE_ADDR(pd, field_desc(${fld_id(src)})), (field_desc(${fld_id(dst)})).bytewidth)
            else:
                addError("generating modify_field", "Improper bytebufs cannot be modified yet.")
    elif isinstance(src, p4_signature_ref):
        p = "parameters.%s" % str(fun.signature[src.idx])
        l = fun.signature_widths[src.idx]
        if dst.width <= 32 and l <= 32:
            #[ MODIFY_INT32_BYTEBUF(pd, ${fld_id(dst)}, ${p}, ${(l+7)/8})
        else:
            if dst.width % 8 == 0 and dst.offset % 8 == 0 and l % 8 == 0: #and dst.instance.metadata:
                #[ MODIFY_BYTEBUF_BYTEBUF(pd, ${fld_id(dst)}, ${p}, (field_desc(${fld_id(dst)})).bytewidth)
            else:
                addError("generating modify_field", "Improper bytebufs cannot be modified yet.")        
    return generated_code

# =============================================================================
# ADD_TO_FIELD

def add_to_field(fun, call):
    generated_code = ""
    args = call[1]
    dst = args[0]
    val = args[1]
    if not isinstance(dst, p4_field):
        addError("generating add_to_field", "We do not allow changing an R-REF yet")
    if isinstance(val, int):
        #[ value32 = ${val};
        if dst.width <= 32:
            #[ ${ extract_int32(dst, 'res32') }
            if (p4_header_keywords.saturating in dst.attributes):
               #[ ${ add_with_saturating('value32', 'res32', dst.width, (p4_header_keywords.signed in dst.attributes)) }
            else:
                #[ value32 += res32;
            #[ ${ modify_int32_int32(dst) }
        else:
            addError("generating modify_field", "Bytebufs cannot be modified yet.")
    elif isinstance(val, p4_field):
        if dst.width <= 32 and val.length <= 32:
            #[ ${ extract_int32(val, 'value32') }
            #[ ${ extract_int32(dst, 'res32') }
            if (p4_header_keywords.saturating in dst.attributes):
               #[ ${ add_with_saturating('value32', 'res32', dst.width, (p4_header_keywords.signed in dst.attributes)) }
            else:
                #[ value32 += res32;
            #[ ${ modify_int32_int32(dst) }
        else:
            addError("generating add_to_field", "bytebufs cannot be modified yet.")
    elif isinstance(val, p4_signature_ref):
        p = "parameters.%s" % str(fun.signature[val.idx])
        l = fun.signature_widths[val.idx]
        if dst.width <= 32 and l <= 32:
            #[ ${ extract_int32(dst, 'res32') }
            #[ TODO
        else:
            addError("generating add_to_field", "bytebufs cannot be modified yet.")
    return generated_code

# =============================================================================
# COUNT

def count(fun, call):
    generated_code = ""
    args = call[1]
    counter = args[0]
    index = args[1]
    if isinstance(index, int): # TODO
        #[ value32 = ${index};
    elif isinstance(index, p4_field): # TODO
        #[ ${ extract_int32(index, 'value32') }
    elif isinstance(val, p4_signature_ref):
        #[ value32 = TODO;
    #[ increase_counter(COUNTER_${counter.name}, value32);
    return generated_code

# =============================================================================
# REGISTER_READ

rc = 0

def register_read(fun, call):
    global rc
    generated_code = ""
    args = call[1]
    dst = args[0] # field
    register = args[1]
    index = args[2]
    if isinstance(index, int): # TODO
        #[ value32 = ${index};
    elif isinstance(index, p4_field): # TODO
        #[ ${ extract_int32(index, 'value32') }
    elif isinstance(val, p4_signature_ref):
        #[ value32 = TODO;
    #[ uint8_t register_value_${rc}[${(register.width+7)/8}];
    #[ read_register(REGISTER_${register.name}, value32, register_value_${rc});
    if register.width > 32:
        addWarning("register_read", "register value trimmed to 32 bits, sorry about that")
    #[ memcpy(&value32, register_value_${rc}, 4);
    if dst.width <= 32:
        #[ ${ modify_int32_int32(dst) }
    else:
        addError("", "Y U using big fields?!?!?!")
    rc = rc + 1
    return generated_code

# =============================================================================
# REGISTER_WRITE

def register_write(fun, call):
    global rc
    generated_code = ""
    args = call[1]
    register = args[0] # field
    index = args[1]
    src = args[2]
    if isinstance(index, int): # TODO
        #[ res32 = ${index};
    elif isinstance(index, p4_field): # TODO
        #[ ${ extract_int32(index, 'res32') }
    elif isinstance(val, p4_signature_ref):
        #[ res32 = TODO;

    if isinstance(src, int):
        #[ value32 = ${src};
    elif isinstance(src, p4_field):
        if register.width <= 32 and src.width <= 32:
            #if src.instance.metadata == register.instance.metadata:
            #    #[ EXTRACT_INT32_BITS(pd, ${fld_id(src)}, value32)
            #else:
                #[ ${ extract_int32(src, 'value32') }
    #[ uint8_t register_value_${rc}[${(register.width+7)/8}];
    #[ memcpy(register_value_${rc}, &value32, 4);
    #[ write_register(REGISTER_${register.name}, res32, register_value_${rc});
    rc = rc + 1
    return generated_code

# =============================================================================
# GENERATE_DIGEST

def generate_digest(fun, call):
    generated_code = ""
    
    ## TODO make this proper
    fun_params = ["bg", "\"mac_learn_digest\""]
    for p in call[1]:
        if isinstance(p, int):
            fun_params += "0" #[str(p)]
        elif isinstance(p, p4_field_list):
            field_list = p
            fun_params += ["&fields"]
        else:
            addError("generating actions.c", "Unhandled parameter type in generate_digest: " + str(p))
 
    #[  struct type_field_list fields;
    quan = str(len(field_list.fields))
    #[    fields.fields_quantity = ${quan};
    #[    fields.field_offsets = malloc(sizeof(uint8_t*)*fields.fields_quantity);
    #[    fields.field_widths = malloc(sizeof(uint8_t*)*fields.fields_quantity);
    for i,field in enumerate(field_list.fields):
        j = str(i)
        if isinstance(field, p4_field):
            #[    fields.field_offsets[${j}] = (uint8_t*) (pd->headers[header_instance_${field.instance}].pointer + field_instance_byte_offset_hdr[field_instance_${field.instance}_${field.name}]);
            #[    fields.field_widths[${j}] = field_instance_bit_width[field_instance_${field.instance}_${field.name}]*8;
        else:
            addError("generating actions.c", "Unhandled parameter type in field_list: " + name + ", " + str(field))

    params = ",".join(fun_params)
    #[
    #[    generate_digest(${params}); sleep(1);
    return generated_code

# =============================================================================
# DROP

def drop(fun, call):
    return "drop(pd);"

# =============================================================================
# PUSH

def push(fun, call):
    generated_code = ""
    args = call[1]
    i = args[0]
    #[ push(pd, header_stack_${i.base_name});
    return generated_code

# =============================================================================
# POP

def pop(fun, call):
    generated_code = ""
    args = call[1]
    i = args[0]
    #[ pop(pd, header_stack_${i.base_name});
    return generated_code

# =============================================================================

for fun in userActions(hlir):
    hasParam = fun.signature
    modifiers = ""
    ret_val_type = "void"
    name = fun.name
    params = ", struct action_%s_params parameters" % (name) if hasParam else ""
    #[ ${modifiers} ${ret_val_type} action_code_${name}(packet_descriptor_t* pd, lookup_table_t** tables ${params}) {
    #[     uint32_t value32, res32;
    #[     (void)value32; (void)res32;
    for i,call in enumerate(fun.call_sequence):
        name = call[0].name 

        # Generates a primitive action call to `name'
        if name in locals().keys():
            #[ ${locals()[name](fun, call)}
        else:
            addWarning("generating actions.c", "Unhandled primitive function: " +  name)

    #[ }
    #[

