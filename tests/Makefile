CFLAGS = -ggdb
TARGETS := test-util.o test-list.o test-list test-util test-percpu
TARGETS += test-syscache test_imports.py
all: $(TARGETS)

test_imports.py: FORCE
	sh gen-import-tests.sh > $@

test-percpu.lds : test-percpu.lds.in build-lds
	./build-lds $< $@

test-percpu: test-percpu.o test-percpu.lds
	$(CC) -o $@ $< -Wl,-T test-percpu.lds

clean:
	rm -f $(TARGETS)

FORCE:
