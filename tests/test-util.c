#include <stdio.h>

struct list_head {
	struct list_head *next;
	struct list_head *prev;
};

struct embedded {
	unsigned long embedded_member1;
	unsigned long embedded_member2;
	struct list_head embedded_list;
};

enum test_enum {
	test1,
	test2,
	test3,
	test4,
};

struct test {
	unsigned long test_member;
	struct {
		unsigned long anon_struct_member1;
		unsigned long anon_struct_member2;
		struct embedded anon_struct_embedded_struct;
	};

	struct {
		unsigned long named_struct_member1;
		unsigned long named_struct_member2;
		struct embedded named_struct_embedded_struct;
	} named_struct;

	union {
		unsigned long anon_union_member1;
		unsigned long anon_union_member2;
		struct embedded anon_union_embedded_struct;
	};

	union {
		unsigned long named_union_member1;
		unsigned long named_union_member2;
		struct embedded named_union_embedded_struct;
	} named_union;

	struct embedded embedded_struct_member;

	int (*function_ptr_member)(struct test *test, int errval);

	enum test_enum enum_member;
};

struct test global_struct_symbol;
unsigned long global_ulong_symbol;
void *global_void_pointer_symbol;

union {
	unsigned long member1;
	void *member2;
} global_union_symbol;

static int test_function_pointer(struct test *test, int errval)
{
	return 0;
}

struct test test_struct = {
	.test_member = 0xdeadbe00,
	/* anon_union { */
	.anon_struct_member1 = 0xdeadbe01,
	.anon_struct_member2 = 0xdeadbe02,
	.anon_struct_embedded_struct = {
		.embedded_member1 = 0xdeadbe03,
		.embedded_member2 = 0xdeadbe04,
		.embedded_list = {
			.next = (struct list_head *)0xdeadbe05UL,
			.prev = (struct list_head *)0xdeadbe06UL,
		},
	},
	/* }, */
	.named_struct = {
		.named_struct_member1 = 0xdeadbe07,
		.named_struct_member2 = 0xdeadbe08,
		.named_struct_embedded_struct = {
			.embedded_member1 = 0xdeadbe09,
			.embedded_member2 = 0xdeadbe0A,
			.embedded_list = {
				.next = (struct list_head *)0xdeadbe0BUL,
				.prev = (struct list_head *)0xdeadbe0CUL,
			},
		},
	},
	/* .anon_union_member1 = 0xdeadbe0D, */
	/* .anon_union_member2 = 0xdeadbe0E, */
	.anon_union_embedded_struct = {
		.embedded_member1 = 0xdeadbe0D,
		.embedded_member2 = 0xdeadbe0E,
		.embedded_list = {
			.next = (struct list_head *)0xdeadbe0FUL,
			.prev = (struct list_head *)0xdeadbe10UL,
		},
	},
	.named_union = {
		/* .named_union_member1 = 0xdeadbe11, */
		/* .named_union_member2 = 0xdeadbe12, */
		.named_union_embedded_struct = {
			.embedded_member1 = 0xdeadbe11,
			.embedded_member2 = 0xdeadbe12,
			.embedded_list = {
				.next = (struct list_head *)0xdeadbe13UL,
				.prev = (struct list_head *)0xdeadbe14UL,
			},
		},
	},
	.embedded_struct_member = {
		.embedded_member1 = 0xdeadbe15,
		.embedded_member2 = 0xdeadbe16,
		.embedded_list = {
			.next = (struct list_head *)0xdeadbe17UL,
			.prev = (struct list_head *)0xdeadbe18UL,
		},
	},
	.function_ptr_member = test_function_pointer,
	.enum_member = test4,
};

unsigned long global_array[5] = {
	0xdeadbeef,
	0xdeadbef0,
	0xdeadbef1,
	0xdeadbef2,
	0xdeadbef3,
};

int
main(void)
{
	struct test test;
	printf("test.test_member = %lx\n", test.test_member);
	printf("global_symbol.test_member = %lx\n", global_struct_symbol.test_member);
	printf("global_ulong_symbol = %lx\n", global_ulong_symbol);
	printf("global_void_pointer_symbol = %lx\n", global_void_pointer_symbol);
	return 0;
}
