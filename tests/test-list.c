#include <stdio.h>

struct list_head {
	struct list_head *next;
	struct list_head *prev;
};

extern struct list_head normal_head;

struct list_head short_list[] = {
	{
		.next = &short_list[1],
		.prev = &normal_head,
	},
	{
		.next = &short_list[2],
		.prev = &short_list[0],
	},
	{
		.next = &short_list[3],
		.prev = &short_list[1],
	},
	{
		.next = &short_list[4],
		.prev = &short_list[2],
	},
	{
		.next = &normal_head,
		.prev = &short_list[3],
	},
};

struct list_head normal_head = {
	.next = &short_list[0],
	.prev = &short_list[4],
};

extern struct list_head cycle_head;
struct list_head short_list_with_cycle[] = {
	{
		.next = &short_list_with_cycle[1],
		.prev = &cycle_head,
	},
	{
		.next = &short_list_with_cycle[2],
		.prev = &short_list_with_cycle[0],
	},
	{
		.next = &short_list_with_cycle[3],
		.prev = &short_list_with_cycle[1],
	},
	{
		.next = &short_list_with_cycle[1],
		.prev = &short_list_with_cycle[2],
	},
	{
		.next = &cycle_head,
		.prev = &short_list_with_cycle[3],
	},
};

struct list_head cycle_head = {
	.next = &short_list_with_cycle[0],
	.prev = &short_list_with_cycle[4],
};

extern struct list_head bad_list_head;
struct list_head short_list_with_bad_prev[] = {
	{
		.next = &short_list_with_bad_prev[1],
		.prev = &bad_list_head,
	},
	{
		.next = &short_list_with_bad_prev[2],
		.prev = &short_list_with_bad_prev[0],
	},
	{
		.next = &short_list_with_bad_prev[3],
		.prev = &short_list_with_bad_prev[0],
	},
	{
		.next = &short_list_with_bad_prev[1],
		.prev = &short_list_with_bad_prev[2],
	},
	{
		.next = &bad_list_head,
		.prev = &short_list_with_bad_prev[3],
	},
};

struct list_head bad_list_head = {
	.next = &short_list[0],
	.prev = &short_list[4],
};

struct container {
	unsigned long someval;
	struct list_head list;
};

extern struct list_head good_container_list;
struct container good_containers[] = {
	{
		.someval = 0xdead0000,
		.list = {
			.next = &good_containers[1].list,
			.prev = &good_container_list,
		},
	},
	{
		.someval = 0xdead0001,
		.list = {
			.next = &good_containers[2].list,
			.prev = &good_containers[0].list,
		},
	},
	{
		.someval = 0xdead0002,
		.list = {
			.next = &good_containers[3].list,
			.prev = &good_containers[1].list,
		},
	},
	{
		.someval = 0xdead0003,
		.list = {
			.next = &good_containers[4].list,
			.prev = &good_containers[2].list,
		},
	},
	{
		.someval = 0xdead0004,
		.list = {
			.next = &good_container_list,
			.prev = &good_containers[3].list,
		},
	},
};

struct list_head good_container_list = {
	.next = &good_containers[0].list,
	.prev = &good_containers[4].list,
};

extern struct list_head cycle_container_list;
struct container cycle_containers[] = {
	{
		.someval = 0xdead0000,
		.list = {
			.next = &cycle_containers[1].list,
			.prev = &cycle_container_list,
		},
	},
	{
		.someval = 0xdead0001,
		.list = {
			.next = &cycle_containers[2].list,
			.prev = &cycle_containers[0].list,
		},
	},
	{
		.someval = 0xdead0002,
		.list = {
			.next = &cycle_containers[3].list,
			.prev = &cycle_containers[1].list,
		},
	},
	{
		.someval = 0xdead0003,
		.list = {
			.next = &cycle_containers[1].list,
			.prev = &cycle_containers[2].list,
		},
	},
	{
		.someval = 0xdead0004,
		.list = {
			.next = &cycle_container_list,
			.prev = &cycle_containers[3].list,
		},
	},
};

struct list_head cycle_container_list = {
	.next = &cycle_containers[0].list,
	.prev = &cycle_containers[4].list,
};

extern struct list_head bad_container_list;
struct container bad_containers[] = {
	{
		.someval = 0xdead0000,
		.list = {
			.next = &bad_containers[1].list,
			.prev = &bad_container_list,
		},
	},
	{
		.someval = 0xdead0001,
		.list = {
			.next = &bad_containers[2].list,
			.prev = &bad_containers[0].list,
		},
	},
	{
		.someval = 0xdead0002,
		.list = {
			.next = &bad_containers[3].list,
			.prev = &bad_containers[1].list,
		},
	},
	{
		.someval = 0xdead0003,
		.list = {
			.next = &bad_containers[4].list,
			.prev = &bad_containers[1].list,
		},
	},
	{
		.someval = 0xdead0004,
		.list = {
			.next = &bad_container_list,
			.prev = &bad_containers[3].list,
		},
	},
};

struct list_head bad_container_list = {
	.next = &bad_containers[0].list,
	.prev = &bad_containers[4].list,
};

struct list_head bad_next_ptr_list = {
	.next = (struct list_head *)0xdeadbeef,
	.prev = &bad_next_ptr_list,
};

struct list_head bad_prev_ptr_list = {
	.next = &bad_prev_ptr_list,
	.prev = (struct list_head *)0xdeadbeef,
};

int
main(void)
{
	struct list_head lh = { NULL, NULL };
	printf("normal_head = %p\n", &normal_head);
	printf("short_list = %p\n", &short_list);
	return 0;
}
