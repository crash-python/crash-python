#include <stdlib.h>
#include <unistd.h>

#define NR_CPUS 32
#define __section(S) __attribute__ ((__section__(#S)))
#define DEFINE_PER_CPU(type, name) \
	__section(.data..percpu) __typeof__(type) name

/* Userspace blows up if you have symbols at offset 0, so we fake it */
#define per_cpu_offset(x) (__per_cpu_offset[x] - (unsigned long)&__per_cpu_start)

# define RELOC_HIDE(ptr, off)                                   \
  ({ unsigned long __ptr;                                       \
     __ptr = (unsigned long) (ptr);                             \
    (typeof(ptr)) (__ptr + (off)); })

#define SHIFT_PERCPU_PTR(__p, __offset)                                 \
        RELOC_HIDE((typeof(*(__p)) *)(__p), (__offset))

#define per_cpu_ptr(ptr, cpu)                                           \
({                                                                      \
        SHIFT_PERCPU_PTR((ptr), per_cpu_offset((cpu)));                 \
})

#define raw_per_cpu_ptr(ptr, cpu)        SHIFT_PERCPU_PTR((ptr), per_cpu_offset((cpu)))
#define raw_cpu_write(ptr, cpu, val) 		\
({						\
	*raw_per_cpu_ptr((ptr), cpu) = val;	\
})

struct test_struct {
	int x;
	unsigned long ulong;
	void *ptr;
};

unsigned long __per_cpu_offset[NR_CPUS];

DEFINE_PER_CPU(struct test_struct, struct_test);
DEFINE_PER_CPU(unsigned long, ulong_test);
DEFINE_PER_CPU(void *, voidp_test);
DEFINE_PER_CPU(struct test_struct *, ptr_to_struct_test);
DEFINE_PER_CPU(unsigned long *, ptr_to_ulong_test);

extern unsigned long __per_cpu_start;
extern unsigned long __per_cpu_end;
extern unsigned long __per_cpu_load;

struct test_struct *percpu_test;
struct test_struct *non_percpu_test;

int
main(void)
{
	int i;
	unsigned long size = (void *)&__per_cpu_end - (void *)&__per_cpu_start;

	for (i = 0; i < NR_CPUS; i++)
	{
		int ret;
		struct test_struct *f;
		void *ptr;
		unsigned long *l;

		ret = posix_memalign(&ptr, 4096, size);
		if (ret)
			return 1;

		__per_cpu_offset[i] = (unsigned long)ptr;

		f = per_cpu_ptr(&struct_test, i);
		f->x = i;
		f->ulong = i;
		f->ptr = NULL;

		raw_cpu_write(&ulong_test, i, i);
		raw_cpu_write(&voidp_test, i, (void *)0xdeadbeef);
		raw_cpu_write(&ptr_to_struct_test, i, f);
		raw_cpu_write(&ptr_to_ulong_test, i, &f->ulong);
	}

	percpu_test = &struct_test;
	non_percpu_test = per_cpu_ptr(&struct_test, 0);

	/* We want to give gdb a core dump to work with */
	abort();
	return 0;
}
