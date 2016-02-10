CFLAGS = -ggdb
<<<<<<< HEAD
TARGETS := test-util.o test-list.o test-list test-util test-percpu
all: $(TARGETS)

test-percpu.lds : test-percpu.lds.in build-lds
	./build-lds $< $@

test-percpu: test-percpu.o test-percpu.lds
	$(CC) -o $@ $< -Wl,-T test-percpu.lds

clean:
	rm -f $(TARGETS)
