GZIPCMD = /usr/bin/gzip
INSTALL = /usr/bin/install -c

PYLINT_ARGS ?= --rcfile tests/pylintrc -r n

ifeq ($(E),1)
PYLINT_ARGS +=  -E
endif

all: clean build doc test

doc-source-clean:
	rm -f doc-source/crash/*.rst doc-source/kdump/*.rst
	rm -f doc-source/commands/*.rst

doc-clean: doc-source-clean
	rm -rf docs

clean: doc-clean man-clean
	make -C tests clean
	rm -rf build

build: doc-help FORCE
	python3 setup.py -q build

clean-build: clean build

datadir ?= /usr/share
pkgdatadir = $(datadir)/crash-python

ifneq ($(DESTDIR),)
ROOT=--root $(DESTDIR)
endif

install: man-install build
	python3 setup.py install $(ROOT)
	install -m 755 -d $(DESTDIR)$(pkgdatadir)
	install -m 644 -t $(DESTDIR)$(pkgdatadir) test-gdb-compatibility.gdbinit

unit-tests: clean-build
	make -C tests -s
	sh tests/run-tests.sh

lint: clean-build
	sh tests/run-pylint.sh $(PYLINT_ARGS) crash kdump

static-check: clean-build
	sh tests/run-static-checks.sh

live-tests: clean-build
	sh tests/run-kernel-tests.sh $(INI_FILES)

test: unit-tests static-check lint live-tests
	@echo -n

full-test: test doc


pycrash.1 : crash-python.1

%.1 : doc-source/%.rst doc-source/conf.py
	sphinx-build -a -b man doc-source .

%.1.gz : %.1
	$(GZIPCMD) -n -c $< > $@

GZ_MAN1 :=  pycrash.1.gz crash-python.1.gz
MAN1 := $(patsubst %.asciidoc,%.1.gz,$(MAN1_TXT))

man: $(GZ_MAN1)

man-clean: FORCE
	rm -f $(GZ_MAN1)
	rm -f pycrash.1 crash-python.1

man-install: man
	$(INSTALL) -d -m 755 $(DESTDIR)$(man1dir)
	$(INSTALL) -m 644 $(GZ_MAN1) $(DESTDIR)$(man1dir)

doc-html: doc-source-clean
	sphinx-build -a -b html doc-source docs/html

doc-help: doc-source-clean
	sphinx-build -a -b text doc-source docs/text

doc: doc-source-clean doc-html doc-help man FORCE

FORCE:
