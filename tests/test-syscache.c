#include <stdio.h>
#include <linux/utsname.h>

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

int
main(void)
{
	printf("%p\n", &init_uts_ns);
	return 0;
}
