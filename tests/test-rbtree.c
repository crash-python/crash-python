#include <stdlib.h>

#define	RB_RED		0
#define	RB_BLACK	1
#define mk_par(p, c) ((unsigned long) (p) | (c))

struct rb_node {
	unsigned long  __rb_parent_color;
	struct rb_node *rb_right;
	struct rb_node *rb_left;
};

struct rb_root {
	struct rb_node *rb_node;
};

struct number_node {
	int v;
	struct rb_node rb;
};

struct rb_node naked_node;
struct rb_root empty_tree_root;
struct rb_root singular_tree_root;
struct rb_root full_binary_tree_root;
struct rb_root linear_binary_tree_root;


int
main(void)
{
	/* The tree structure cannot be initialized statically (because
	 * __rb_parent_color is initialized with non-const expression) so
	 * allocate it in runtime (stack is mostly unused besides these) and
	 * publish the pointer in the global variable to find it easily via
	 * gdb. */
	struct rb_node singular_tree[] = {
		{
			.__rb_parent_color = mk_par(NULL, RB_BLACK),
			.rb_right = NULL,
			.rb_left  = NULL,
		},
	};
	singular_tree_root.rb_node = &singular_tree[0];

	struct number_node full_binary_tree[] = {
		{
			.v = 0,
			.rb = {
				.__rb_parent_color = mk_par(NULL, RB_BLACK),
				.rb_right = &full_binary_tree[2].rb,
				.rb_left  = &full_binary_tree[1].rb,
			},
		},
		{
			.v = 1,
			.rb = {
				.__rb_parent_color = mk_par(&full_binary_tree[0].rb, RB_RED),
				.rb_right = &full_binary_tree[4].rb,
				.rb_left  = &full_binary_tree[3].rb,
			},
		},
		{
			.v = 2,
			.rb = {
				.__rb_parent_color = mk_par(&full_binary_tree[0].rb, RB_RED),
				.rb_right = &full_binary_tree[6].rb,
				.rb_left  = &full_binary_tree[5].rb,
			},
		},
		{
			.v = 3,
			.rb = {
				.__rb_parent_color = mk_par(&full_binary_tree[1].rb, RB_BLACK),
				.rb_right = NULL,
				.rb_left  = NULL,
			},
		},
		{
			.v = 4,
			.rb = {
				.__rb_parent_color = mk_par(&full_binary_tree[1].rb, RB_BLACK),
				.rb_right = NULL,
				.rb_left  = NULL,
			},
		},
		{
			.v = 5,
			.rb = {
				.__rb_parent_color = mk_par(&full_binary_tree[2].rb, RB_BLACK),
				.rb_right = NULL,
				.rb_left  = NULL,
			},
		},
		{
			.v = 6,
			.rb = {
				.__rb_parent_color = mk_par(&full_binary_tree[2].rb, RB_BLACK),
				.rb_right = NULL,
				.rb_left  = NULL,
			},
		},
	};
	full_binary_tree_root.rb_node = &full_binary_tree[0].rb;

	/* Not a true RB tree but good for testing */
	struct number_node linear_binary_tree[] = {
		{
			.v = 0,
			.rb = {
				.__rb_parent_color = mk_par(NULL, RB_BLACK),
				.rb_right = NULL,
				.rb_left  = &linear_binary_tree[1].rb,
			},
		},
		{
			.v = 1,
			.rb = {
				.__rb_parent_color = mk_par(&linear_binary_tree[0].rb, RB_RED),
				.rb_right = &linear_binary_tree[2].rb,
				.rb_left  = NULL,
			},
		},
		{
			.v = 2,
			.rb = {
				.__rb_parent_color = mk_par(&linear_binary_tree[1].rb, RB_BLACK),
				.rb_right = NULL,
				.rb_left  = NULL,
			},
		},
	};
	linear_binary_tree_root.rb_node = &linear_binary_tree[0].rb;
	
	(void)&empty_tree_root;
	(void)&singular_tree_root;
	(void)&full_binary_tree_root;

	/* We want to give gdb a core dump to work with */
	abort();
	return 0;
}
