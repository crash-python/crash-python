#!/usr/bin/env python
# -*- coding: utf-8 -*-,
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

from __future__ import print_function

import crash.commands
import crash.commands.struct
import unittest
import gdb

def debug_out(actual, expected=None):
    print("\n--- actual ---")
    print("\n".join(actual))
    if expected:
        print("--- expected ---")
        print(expected)
    print("---")

# All of these strings will be formatted - use escaped brackets
test_print_all_output = \
"""struct test {{
    long unsigned int test_member;
    struct {{
        long unsigned int anon_struct_member1;
        long unsigned int anon_struct_member2;
        struct embedded anon_struct_embedded_struct;
    }};
    struct {{
        long unsigned int named_struct_member1;
        long unsigned int named_struct_member2;
        struct embedded named_struct_embedded_struct;
    }} named_struct;
    union {{
        long unsigned int anon_union_member1;
        long unsigned int anon_union_member2;
        struct embedded anon_union_embedded_struct;
    }};
    union {{
        long unsigned int named_union_member1;
        long unsigned int named_union_member2;
        struct embedded named_union_embedded_struct;
    }} named_union;
    struct embedded embedded_struct_member;
    int (*function_ptr_member)(struct test *, int);
    enum test_enum enum_member;
}}
SIZE: {}"""

test_print_all_offset_output = \
"""struct test {{
    [{}] long unsigned int test_member;
        struct {{
    [{}]     long unsigned int anon_struct_member1;
   [{}]     long unsigned int anon_struct_member2;
   [{}]     struct embedded anon_struct_embedded_struct;
        }};
        struct {{
   [{}]     long unsigned int named_struct_member1;
   [{}]     long unsigned int named_struct_member2;
   [{}]     struct embedded named_struct_embedded_struct;
        }} named_struct;
        union {{
  [{}]     long unsigned int anon_union_member1;
  [{}]     long unsigned int anon_union_member2;
  [{}]     struct embedded anon_union_embedded_struct;
        }};
        union {{
  [{}]     long unsigned int named_union_member1;
  [{}]     long unsigned int named_union_member2;
  [{}]     struct embedded named_union_embedded_struct;
        }} named_union;
  [{}] struct embedded embedded_struct_member;
  [{}] int (*function_ptr_member)(struct test *, int);
  [{}] enum test_enum enum_member;
}}
SIZE: {}"""

test_print_all_offset_address_output = \
"""struct test {{
  [{1:0{0}x}] long unsigned int test_member;
                     struct {{
  [{2:0{0}x}]     long unsigned int anon_struct_member1;
  [{3:0{0}x}]     long unsigned int anon_struct_member2;
  [{4:0{0}x}]     struct embedded anon_struct_embedded_struct;
                     }};
                     struct {{
  [{5:0{0}x}]     long unsigned int named_struct_member1;
  [{6:0{0}x}]     long unsigned int named_struct_member2;
  [{7:0{0}x}]     struct embedded named_struct_embedded_struct;
                     }} named_struct;
                     union {{
  [{8:0{0}x}]     long unsigned int anon_union_member1;
  [{9:0{0}x}]     long unsigned int anon_union_member2;
  [{10:0{0}x}]     struct embedded anon_union_embedded_struct;
                     }};
                     union {{
  [{11:0{0}x}]     long unsigned int named_union_member1;
  [{12:0{0}x}]     long unsigned int named_union_member2;
  [{13:0{0}x}]     struct embedded named_union_embedded_struct;
                     }} named_union;
  [{14:0{0}x}] struct embedded embedded_struct_member;
  [{15:0{0}x}] int (*function_ptr_member)(struct test *, int);
  [{16:0{0}x}] enum test_enum enum_member;
}}
SIZE: {17}"""

test_print_test_member_output = \
"""struct test {{
    long unsigned int test_member;
}}
SIZE: {}"""

test_print_test_member_offset_output = \
"""struct test {{
    [0] long unsigned int test_member;
}}
SIZE: {}"""

test_print_anon_struct_output = \
"""struct test {{
    struct {{
        {} {};
    }};
}}
SIZE: {}"""
test_print_anon_struct_output = \
"""struct test {{
    struct {{
        {} {};
    }};
}}
SIZE: {}"""

test_print_anon_struct_offset_output_1_digit = \
"""struct test {{
        struct {{
    [{}]     {} {};
        }};
}}
SIZE: {}"""

test_print_anon_struct_offset_output_2_digit = \
"""struct test {{
        struct {{
   [{}]     {} {};
        }};
}}
SIZE: {}"""

test_print_anon_struct_embedded_struct_member_output = \
"""struct test {{
    struct {{
        struct embedded {{
            {} {};
        }} anon_struct_embedded_struct;
    }};
}}
SIZE: {}"""

test_print_anon_struct_embedded_struct_member_offset_output = \
"""struct test {{
        struct {{
            struct embedded {{
   [{}]         {} {};
            }} anon_struct_embedded_struct;
        }};
}}
SIZE: {}"""


test_print_named_struct_output = \
"""struct test {{
    struct {{
        {} {};
    }} named_struct;
}}
SIZE: {}"""

test_print_named_struct_offset_output = \
"""struct test {{
        struct {{
   [{}]     {} {};
        }} named_struct;
}}
SIZE: {}"""

test_print_named_struct_embedded_struct_member_output = \
"""struct test {{
    struct {{
        struct embedded {{
            {} {};
        }} named_struct_embedded_struct;
    }} named_struct;
}}
SIZE: {}"""

test_print_named_struct_embedded_struct_member_offset_output = \
"""struct test {{
        struct {{
            struct embedded {{
   [{}]         {} {};
            }} named_struct_embedded_struct;
        }} named_struct;
}}
SIZE: {}"""


test_print_named_struct_embedded_struct_list_output = \
"""struct test {{
    struct {{
        struct embedded {{
            struct list_head {{
                {} {};
            }} embedded_list;
        }} named_struct_embedded_struct;
    }} named_struct;
}}
SIZE: {}"""

test_print_named_struct_embedded_struct_list_offset_output = \
"""struct test {{
        struct {{
            struct embedded {{
                struct list_head {{
   [{}]             {} {};
                }} embedded_list;
            }} named_struct_embedded_struct;
        }} named_struct;
}}
SIZE: {}"""

test_print_anon_union_output = \
"""struct test {{
    union {{
        {} {};
    }};
}}
SIZE: {}"""

test_print_anon_union_offset_output = \
"""struct test {{
        union {{
  [{}]     {} {};
        }};
}}
SIZE: {}"""

test_print_anon_union_embedded_struct_output = \
"""struct test {{
    union {{
        struct embedded {{
            {} {};
        }} anon_union_embedded_struct;
    }};
}}
SIZE: {}"""

test_print_anon_union_embedded_struct_offset_output = \
"""struct test {{
        union {{
            struct embedded {{
  [{}]         {} {};
            }} anon_union_embedded_struct;
        }};
}}
SIZE: {}"""

test_print_named_union_output = \
"""struct test {{
    union {{
        {} {};
    }} named_union;
}}
SIZE: {}"""

test_print_named_union_offset_output = \
"""struct test {{
        union {{
  [{}]     {} {};
        }} named_union;
}}
SIZE: {}"""

test_print_named_union_embedded_struct_output = \
"""struct test {{
    union {{
        struct embedded {{
            {} {};
        }} named_union_embedded_struct;
    }} named_union;
}}
SIZE: {}"""

test_print_named_union_embedded_struct_offset_output = \
"""struct test {{
        union {{
            struct embedded {{
  [{}]         {} {};
            }} named_union_embedded_struct;
        }} named_union;
}}
SIZE: {}"""

test_print_embedded_struct_output = \
"""struct test {{
    struct embedded embedded_struct_member;
}}
SIZE: {}"""

test_print_embedded_struct_offset_output = \
"""struct test {{
  [168] struct embedded embedded_struct_member;
}}
SIZE: {}"""

test_print_embedded_struct_member_output = \
"""struct test {{
    struct embedded {{
        {} {};
    }} embedded_struct_member;
}}
SIZE: {}"""

test_print_embedded_struct_member_offset_output = \
"""struct test {{
        struct embedded {{
  [{}]     {} {};
        }} embedded_struct_member;
}}
SIZE: {}"""

test_print_embedded_struct_list_output = \
"""struct test {{
    struct embedded {{
        struct list_head {{
            {} {};
        }} embedded_list;
    }} embedded_struct_member;
}}
SIZE: {}"""

test_print_embedded_struct_list_offset_output = \
"""struct test {{
        struct embedded {{
            struct list_head {{
  [{}]         {} {};
            }} embedded_list;
        }} embedded_struct_member;
}}
SIZE: {}"""

test_print_enum_output = \
"""struct test {{
    enum test_enum enum_member;
}}
SIZE: {}"""

test_print_enum_offset_output = \
"""struct test {{
  [{}] enum test_enum enum_member;
}}
SIZE: {}"""

test_print_enum_offset_address_output = \
"""struct test {{
  [{1:0{0}x}] enum test_enum enum_member;
}}
SIZE: {2}"""

test_print_multi1_output = \
"""struct test {{
    long unsigned int test_member;
    struct {{
        long unsigned int named_struct_member2;
    }} named_struct;
}}
SIZE: {}"""

test_print_multi1_offset_output = \
"""struct test {{
    [{}] long unsigned int test_member;
        struct {{
   [{}]     long unsigned int named_struct_member2;
        }} named_struct;
}}
SIZE: {}"""

test_print_multi1_offset_address_output = \
"""struct test {{
  [{1:0{0}x}] long unsigned int test_member;
                     struct {{
  [{2:0{0}x}]     long unsigned int named_struct_member2;
                     }} named_struct;
}}
SIZE: {3}"""

test_print_func_pointer_output = \
"""struct test {{
    int (*function_ptr_member)(struct test *, int);
}}
SIZE: {}"""

test_print_func_pointer_offset_output = \
"""struct test {{
  [{}] int (*function_ptr_member)(struct test *, int);
}}
SIZE: {}"""
test_print_func_pointer_offset_address_output = \
"""struct test {{
  [{1:0{0}x}] int (*function_ptr_member)(struct test *, int);
}}
SIZE: {2}"""


class TestUtil(unittest.TestCase):
    def setUp(self):
        gdb.execute("set print pretty on")
        gdb.execute("file tests/test-util.o")
	self.struct = crash.commands.struct.StructCommand()
        self.ulongsize = gdb.lookup_type('unsigned long').sizeof
        self.test_struct = gdb.lookup_type("struct test")
        sym = gdb.lookup_global_symbol("test_struct")
        if not sym:
            raise Exception("cannot find test_struct")
        self.test_struct_sym = sym.value()


    def test_is_func_ptr_good(self):
        self.assertTrue(self.struct.is_func_ptr(
                                    self.test_struct['function_ptr_member']))

    def test_is_func_ptr_bad(self):
        self.assertFalse(self.struct.is_func_ptr(
                                    self.test_struct['enum_member']))

    def test_format_function_pointer_good(self):
        output = self.struct.format_func_ptr('function_ptr_member',
                                self.test_struct['function_ptr_member'].type)
        expected = "int (*function_ptr_member)(struct test *, int)"

        self.assertTrue(output == expected)

    def test_print_all(self):
        template = test_print_all_output
        output = self.struct.format_struct_layout(self.test_struct, False,
                                                  None, None)

        expected = template.format(self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_all_offset(self):
        template = test_print_all_offset_output
        output = self.struct.format_struct_layout(self.test_struct, True, None, None)

        expected = template.format(0,
                                   self.ulongsize*1,
                                   self.ulongsize*2,
                                   self.ulongsize*3, # embedded = 4 longs
                                   self.ulongsize*7,
                                   self.ulongsize*8,
                                   self.ulongsize*9, # embedded = 4 longs
                                   self.ulongsize*13,
                                   self.ulongsize*13,
                                   self.ulongsize*13, # embedded = 4 longs
                                   self.ulongsize*17,
                                   self.ulongsize*17,
                                   self.ulongsize*17, # embedded = 4 longs
                                   self.ulongsize*21, # embedded = 4 longs
                                   self.ulongsize*25,
                                   self.ulongsize*26,
                                   self.test_struct.sizeof)

        self.assertTrue("\n".join(output) == expected)

    def test_print_all_offset_address(self):
        baseaddr = long(self.test_struct_sym.address)
        template = test_print_all_offset_address_output
        output = self.struct.format_struct_layout(self.test_struct, True,
                                         baseaddr, None)
        expected = template.format(self.ulongsize*2,
                                   baseaddr + self.ulongsize*0,
                                   baseaddr + self.ulongsize*1,
                                   baseaddr + self.ulongsize*2,
                                   baseaddr + self.ulongsize*3,
                                   baseaddr + self.ulongsize*7,
                                   baseaddr + self.ulongsize*8,
                                   baseaddr + self.ulongsize*9,
                                   baseaddr + self.ulongsize*13,
                                   baseaddr + self.ulongsize*13,
                                   baseaddr + self.ulongsize*13,
                                   baseaddr + self.ulongsize*17,
                                   baseaddr + self.ulongsize*17,
                                   baseaddr + self.ulongsize*17,
                                   baseaddr + self.ulongsize*21,
                                   baseaddr + self.ulongsize*25,
                                   baseaddr + self.ulongsize*26,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_test_member(self):
        template = test_print_test_member_output

        output = self.struct.format_struct_layout(self.test_struct, False, None,
                                         ['test_member'])
        expected = template.format(self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_test_member_offset(self):
        template = test_print_test_member_offset_output
        output = self.struct.format_struct_layout(self.test_struct, True, None,
                                         ['test_member'])
        expected = template.format(self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_struct_member1(self):
        member = "anon_struct_member1"
        member_type = "long unsigned int"
        template = test_print_anon_struct_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member, self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_struct_member1_offset(self):
        member = "anon_struct_member1"
        member_type = "long unsigned int"

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = self.ulongsize
        if offset > 10:
            template = test_print_anon_struct_offset_output_2_digit
        else:
            template = test_print_anon_struct_offset_output_1_digit
        expected = template.format(offset, member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_struct_member2(self):
        member = "anon_struct_member2"
        member_type = "long unsigned int"
        template = test_print_anon_struct_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member, self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_struct_member2_offset(self):
        member = "anon_struct_member2"
        member_type = "long unsigned int"

        offset = 2*self.ulongsize
        if offset > 10:
            template = test_print_anon_struct_offset_output_2_digit
        else:
            template = test_print_anon_struct_offset_output_1_digit

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        expected = template.format(offset, member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_struct_embedded_struct(self):
        member = "anon_struct_embedded_struct"
        member_type = "struct embedded"
        template = test_print_anon_struct_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member, self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_struct_embedded_struct_offset(self):
        member = "anon_struct_embedded_struct"
        member_type = "struct embedded"

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 3*self.ulongsize
        if offset > 10:
            template = test_print_anon_struct_offset_output_2_digit
        else:
            template = test_print_anon_struct_offset_output_1_digit
        expected = template.format(offset, member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_struct_embedded_struct_member1(self):
        member = "anon_struct_embedded_struct.embedded_member1"
        member_name = "embedded_member1"
        member_type = "long unsigned int"
        template = test_print_anon_struct_embedded_struct_member_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_struct_embedded_struct_member1_offset(self):
        member = "anon_struct_embedded_struct.embedded_member1"
        member_name = "embedded_member1"
        member_type = "long unsigned int"

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 3*self.ulongsize
        if offset > 10:
            template = test_print_anon_struct_offset_output_2_digit
        else:
            template = test_print_anon_struct_offset_output_1_digit
        template = test_print_anon_struct_embedded_struct_member_offset_output
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_member1(self):
        member = "named_struct.named_struct_member1"
        member_name = "named_struct_member1"
        member_type = "long unsigned int"
        template = test_print_named_struct_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_member1_offset(self):
        member = "named_struct.named_struct_member1"
        member_name = "named_struct_member1"
        member_type = "long unsigned int"
        template = test_print_named_struct_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = self.ulongsize*7
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_member2(self):
        member = "named_struct.named_struct_member2"
        member_name = "named_struct_member2"
        member_type = "long unsigned int"
        template = test_print_named_struct_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_member2_offset(self):
        member = "named_struct.named_struct_member2"
        member_name = "named_struct_member2"
        member_type = "long unsigned int"
        template = test_print_named_struct_offset_output

        offset = 8*self.ulongsize
        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct(self):
        member = "named_struct.named_struct_embedded_struct"
        member_name = "named_struct_embedded_struct"
        member_type = "struct embedded"
        template = test_print_named_struct_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_offset(self):
        member = "named_struct.named_struct_embedded_struct"
        member_name = "named_struct_embedded_struct"
        member_type = "struct embedded"
        template = test_print_named_struct_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 9*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_member1(self):
        member = "named_struct.named_struct_embedded_struct.embedded_member1"
        member_name = "embedded_member1"
        member_type = "long unsigned int"
        template = test_print_named_struct_embedded_struct_member_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_member1_offset(self):
        member = "named_struct.named_struct_embedded_struct.embedded_member1"
        member_name = "embedded_member1"
        member_type = "long unsigned int"
        template = test_print_named_struct_embedded_struct_member_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 9*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_member2(self):
        member = "named_struct.named_struct_embedded_struct.embedded_member2"
        member_name = "embedded_member2"
        member_type = "long unsigned int"
        template = test_print_named_struct_embedded_struct_member_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_member2_offset(self):
        member = "named_struct.named_struct_embedded_struct.embedded_member2"
        member_name = "embedded_member2"
        member_type = "long unsigned int"
        template = test_print_named_struct_embedded_struct_member_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 10*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_list(self):
        member = "named_struct.named_struct_embedded_struct.embedded_list"
        member_name = "embedded_list"
        member_type = "struct list_head"
        template = test_print_named_struct_embedded_struct_member_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_list_offset(self):
        member = "named_struct.named_struct_embedded_struct.embedded_list"
        member_name = "embedded_list"
        member_type = "struct list_head"
        template = test_print_named_struct_embedded_struct_member_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 11*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_list_next(self):
        member = "named_struct.named_struct_embedded_struct.embedded_list.next"
        member_name = "next"
        member_type = "struct list_head *"
        template = test_print_named_struct_embedded_struct_list_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_list_next_offset(self):
        member = "named_struct.named_struct_embedded_struct.embedded_list.next"
        member_name = "next"
        member_type = "struct list_head *"
        template = test_print_named_struct_embedded_struct_list_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 11*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_prev_list(self):
        member = "named_struct.named_struct_embedded_struct.embedded_list.prev"
        member_name = "prev"
        member_type = "struct list_head *"
        template = test_print_named_struct_embedded_struct_list_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_struct_embedded_struct_list_prev_offset(self):
        member = "named_struct.named_struct_embedded_struct.embedded_list.prev"
        member_name = "prev"
        member_type = "struct list_head *"
        template = test_print_named_struct_embedded_struct_list_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 12*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_union_member1(self):
        member = "anon_union_member1"
        member_type = "long unsigned int"
        template = test_print_anon_union_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_union_member1_offset(self):
        member = "anon_union_member1"
        member_type = "long unsigned int"
        template = test_print_anon_union_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = self.ulongsize*13
        expected = template.format(offset, member_type, member,
                                  self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_union_member2(self):
        member = "anon_union_member2"
        member_type = "long unsigned int"
        template = test_print_anon_union_output

        offset = self.ulongsize*13
        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_union_member2_offset(self):
        member = "anon_union_member2"
        member_type = "long unsigned int"
        template = test_print_anon_union_offset_output

        offset = self.ulongsize*13
        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        expected = template.format(offset, member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_union_embedded_struct(self):
        member = "anon_union_embedded_struct"
        member_type = "struct embedded"
        template = test_print_anon_union_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_union_embedded_struct_offset(self):
        member = "anon_union_embedded_struct"
        member_type = "struct embedded"

        template = test_print_anon_union_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 13*self.ulongsize
        expected = template.format(offset, member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_union_embedded_struct_member1(self):
        member = "anon_union_embedded_struct.embedded_member1"
        member_type = "long unsigned int"
        member_name = "embedded_member1"
        template = test_print_anon_union_embedded_struct_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_anon_union_embedded_struct_member1_offset(self):
        member = "anon_union_embedded_struct.embedded_member1"
        member_name = "embedded_member1"
        member_type = "long unsigned int"

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 13*self.ulongsize
        template = test_print_anon_union_embedded_struct_offset_output
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_union_member1(self):
        member = "named_union.named_union_member1"
        member_name = "named_union_member1"
        member_type = "long unsigned int"
        template = test_print_named_union_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_union_member1_offset(self):
        member = "named_union.named_union_member1"
        member_name = "named_union_member1"
        member_type = "long unsigned int"
        template = test_print_named_union_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 17*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_union_member2(self):
        member = "named_union.named_union_member2"
        member_name = "named_union_member2"
        member_type = "long unsigned int"
        template = test_print_named_union_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_union_member2_offset(self):
        member = "named_union.named_union_member2"
        member_name = "named_union_member2"
        member_type = "long unsigned int"
        template = test_print_named_union_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 17*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_union_embedded_struct(self):
        member = "named_union.named_union_embedded_struct"
        member_name = "named_union_embedded_struct"
        member_type = "struct embedded"
        template = test_print_named_union_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_union_embedded_struct_offset(self):
        member = "named_union.named_union_embedded_struct"
        member_name = "named_union_embedded_struct"
        member_type = "struct embedded"
        template = test_print_named_union_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 17*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_union_embedded_struct_member1(self):
        member = "named_union.named_union_embedded_struct.embedded_member1"
        member_name = "embedded_member1"
        member_type = "long unsigned int"
        template = test_print_named_union_embedded_struct_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_named_union_embedded_struct_member1_offset(self):
        member = "named_union.named_union_embedded_struct.embedded_member1"
        member_name = "embedded_member1"
        member_type = "long unsigned int"
        template = test_print_named_union_embedded_struct_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 17*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct(self):
        template = test_print_embedded_struct_output
        output = self.struct.format_struct_layout(self.test_struct, False, None,
                            ['embedded_struct_member'])
        expected = template.format(self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_offset(self):
        member_type = "long unsigned int"
        member = "embedded_member1"
        template = test_print_embedded_struct_member_output

        output = self.struct.format_struct_layout(self.test_struct, False, None,
                            ['embedded_struct_member.embedded_member1'])
        expected = template.format(member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_member1(self):
        member_type = "long unsigned int"
        member = "embedded_member1"
        template = test_print_embedded_struct_member_output

        output = self.struct.format_struct_layout(self.test_struct, False, None,
                            ['embedded_struct_member.embedded_member1'])
        expected = template.format(member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_member1_offset(self):
        member_type = "long unsigned int"
        member = "embedded_member1"
        template = test_print_embedded_struct_member_offset_output

        offset = self.ulongsize * 21
        output = self.struct.format_struct_layout(self.test_struct, True, None,
                            ['embedded_struct_member.embedded_member1'])
        expected = template.format(offset, member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_member2(self):
        member_type = "long unsigned int"
        member = "embedded_member2"
        template = test_print_embedded_struct_member_output

        output = self.struct.format_struct_layout(self.test_struct, False, None,
                            ['embedded_struct_member.embedded_member2'])
        expected = template.format(member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_member2_offset(self):
        member_type = "long unsigned int"
        member = "embedded_member2"
        template = test_print_embedded_struct_member_offset_output

        offset = self.ulongsize * 22
        output = self.struct.format_struct_layout(self.test_struct, True, None,
                            ['embedded_struct_member.embedded_member2'])
        expected = template.format(offset, member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_member_list(self):
        member_type = "struct list_head"
        member = "embedded_list"
        template = test_print_embedded_struct_member_output

        output = self.struct.format_struct_layout(self.test_struct, False, None,
                            ['embedded_struct_member.embedded_list'])
        expected = template.format(member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_member_list_offset(self):
        member_type = "struct list_head"
        member = "embedded_list"
        template = test_print_embedded_struct_member_offset_output

        offset = self.ulongsize * 23
        output = self.struct.format_struct_layout(self.test_struct, True, None,
                            ['embedded_struct_member.embedded_list'])
        expected = template.format(offset, member_type, member,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_list_offset(self):
        member = "embedded_struct_member.embedded_list"
        member_name = "embedded_list"
        member_type = "struct list_head"
        template = test_print_embedded_struct_member_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 23*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_list_next(self):
        member = "embedded_struct_member.embedded_list.next"
        member_name = "next"
        member_type = "struct list_head *"
        template = test_print_embedded_struct_list_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_list_next_offset(self):
        member = "embedded_struct_member.embedded_list.next"
        member_name = "next"
        member_type = "struct list_head *"
        template = test_print_embedded_struct_list_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 23*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_prev_list(self):
        member = "embedded_struct_member.embedded_list.prev"
        member_name = "prev"
        member_type = "struct list_head *"
        template = test_print_embedded_struct_list_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, [member])
        expected = template.format(member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_embedded_struct_list_prev_offset(self):
        member = "embedded_struct_member.embedded_list.prev"
        member_name = "prev"
        member_type = "struct list_head *"
        template = test_print_embedded_struct_list_offset_output

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        offset = 24*self.ulongsize
        expected = template.format(offset, member_type, member_name,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_function_pointer(self):
        members = ['function_ptr_member']
        template = test_print_func_pointer_output

        output = self.struct.format_struct_layout(self.test_struct, False, None, members)
        expected = template.format(self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_function_pointer_offset(self):
        members = ['function_ptr_member']
        template = test_print_func_pointer_offset_output
        offset = self.ulongsize*25

        output = self.struct.format_struct_layout(self.test_struct, True, None, members)
        expected = template.format(offset, self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_function_pointer_offset_address(self):
        members = ['function_ptr_member']
        template = test_print_func_pointer_offset_address_output
        baseaddr = long(self.test_struct_sym.address)
        offset = self.ulongsize*25

        output = self.struct.format_struct_layout(self.test_struct, True, baseaddr,
                                         members)
        expected = template.format(self.ulongsize*2, baseaddr + offset,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_enum(self):
        output = self.struct.format_struct_layout(self.test_struct, False, None,
                            ['enum_member'])
        expected = test_print_enum_output.format(self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_enum_offset(self):
        member = "enum_member"
        template = test_print_enum_offset_output
        offset = self.ulongsize*26

        output = self.struct.format_struct_layout(self.test_struct, True, None, [member])
        expected = template.format(offset, self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_enum_address(self):
        template = test_print_multi1_offset_address_output
        baseaddr = long(self.test_struct_sym.address)
        members = ['enum_member']
        template = test_print_enum_offset_address_output
        offset = self.ulongsize*26

        output = self.struct.format_struct_layout(self.test_struct, True, baseaddr,
                                         members)
        expected = template.format(self.ulongsize*2,
                                   baseaddr + offset,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_multi1(self):
        template = test_print_multi1_output
        members = ['test_member', 'named_struct.named_struct_member2']

        output = self.struct.format_struct_layout(self.test_struct, False, None, members)
        expected = template.format(self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_multi1_offset(self):
        template = test_print_multi1_offset_output
        members = ['test_member', 'named_struct.named_struct_member2']

        output = self.struct.format_struct_layout(self.test_struct, True, None, members)
        expected = template.format(0, self.ulongsize*8, self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_print_multi1_offset_address(self):
        template = test_print_multi1_offset_address_output
        baseaddr = long(self.test_struct_sym.address)
        members = ['test_member', 'named_struct.named_struct_member2']

        output = self.struct.format_struct_layout(self.test_struct, True,
                                                  baseaddr, members)
        expected = template.format(self.ulongsize*2,
                                   baseaddr,
                                   baseaddr + self.ulongsize*8,
                                   self.test_struct.sizeof)
        self.assertTrue("\n".join(output) == expected)

    def test_command_offset(self):
        argstr = "test ff0000000000000000 -o"
        args = self.struct.parser.parse_args(gdb.string_to_argv(argstr))
        self.struct.format_output(args)

    def test_command_offset_with_l_offset(self):
        argstr = "test.anon_struct_embedded_struct ff0000000000000000 -o -l test.anon_struct_embedded_struct.embedded_list"
        args = self.struct.parser.parse_args(gdb.string_to_argv(argstr))
        self.struct.format_output(args)

    def test_command(self):
        argstr = "test.anon_struct_embedded_struct test_struct.anon_struct_embedded_struct.embedded_list -l test.anon_struct_embedded_struct.embedded_list"
        args = self.struct.parser.parse_args(gdb.string_to_argv(argstr))
        output = self.struct.format_output(args)
        debug_out(output)

    def test_command_location_structure_mismatch(self):
        argstr = "test test_struct.anon_struct_embedded_struct.embedded_list"
        args = self.struct.parser.parse_args(gdb.string_to_argv(argstr))
        with self.assertRaises(crash.commands.CommandRuntimeError):
            output = self.struct.format_output(args)

    def test_command_location_structure_mismatch_force(self):
        argstr = "test test_struct.anon_struct_embedded_struct.embedded_list -F"
        args = self.struct.parser.parse_args(gdb.string_to_argv(argstr))
        output = self.struct.format_output(args)

    def test_command_invalid_location(self):
        with self.assertRaises(crash.commands.CommandRuntimeError):
            argstr = "test.anon_struct_embedded_struct test_structx.anon_struct_embedded_struct.embedded_list -o -l test.anon_struct_embedded_struct.embedded_list"
            args = self.struct.parser.parse_args(gdb.string_to_argv(argstr))
            self.struct.format_output(args)

    def test_command_invalid_location(self):
        with self.assertRaises(crash.commands.CommandRuntimeError):
            argstr = "test.anon_struct_embedded_struct test_structx.anon_struct_embedded_struct.embedded_list -o -l test.anon_struct_embedded_struct.embedded_list"
            args = self.struct.parser.parse_args(gdb.string_to_argv(argstr))
            self.struct.format_output(args)

    def test_command_sym(self):
        argstr = "test test_struct"
        args = self.struct.parser.parse_args(gdb.string_to_argv(argstr))
        output = self.struct.format_output(args)
        debug_out(output)

