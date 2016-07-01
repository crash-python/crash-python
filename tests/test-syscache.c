#include <stdio.h>
#include <linux/utsname.h>
#include <stdint.h>

struct utsname_test_struct {
	struct new_utsname name;
};

struct utsname_test_struct init_uts_ns = {
	.name = {
		.sysname = "Linux",
		.nodename = "linux",
		.release = "4.4.21-default",
		.version = "#7 SMP Wed Nov 2 16:08:46 EDT 2016",
		.machine = "x86_64",
		.domainname = "suse.de",
	},
};

/* 0:02:34 */
uint64_t jiffies_64 = (uint64_t)((unsigned int)(-300*250)) + (154 * 250);

int
main(void)
{
	printf("%p\n", &init_uts_ns);
	printf("%llu\n", jiffies_64);
	return 0;
}
