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

clean: doc-clean man-clean build-clean
	make -C tests clean

build-clean:
	rm -rf build

build: doc-help FORCE
	python3 setup.py -q build

force-rebuild: build-clean
	python3 setup.py -q build

datadir ?= /usr/share
pkgdatadir = $(datadir)/crash-python

ifneq ($(DESTDIR),)
ROOT=--root $(DESTDIR)
endif

install: man-install doc-help-install doc-text-install doc-html-install build
	python3 setup.py install $(ROOT)
	install -m 755 -d $(DESTDIR)$(pkgdatadir)
	install -m 644 -t $(DESTDIR)$(pkgdatadir) test-gdb-compatibility.gdbinit
	install -m 755 -d $(DESTDIR)/usr/bin
	install -m 755 crash.sh $(DESTDIR)/usr/bin/crash-python
	ln -fs crash-python $(DESTDIR)/usr/bin/pycrash

helpdir=$(pkgdatadir)/help
doc-help-install: doc-help
	install -d $(DESTDIR)$(helpdir)/commands
	install -t $(DESTDIR)$(helpdir)/commands docs/text/commands/*.txt

docdir=$(datadir)/doc/packages/crash-python
textdir=$(docdir)/text

doc-text-install: doc-help
	install -m 755 -d $(DESTDIR)$(textdir)/crash
	install -m 644 -t $(DESTDIR)$(textdir)/crash docs/text/crash/*.txt
	install -m 755 -d $(DESTDIR)$(textdir)/kdump
	install -m 644 -t $(DESTDIR)$(textdir)/kdump docs/text/kdump/*.txt
	install -m 644 -t $(DESTDIR)$(textdir) docs/text/*.txt

htmldir=$(docdir)/html
doc-html-install: doc-html
	install -m 755 -d $(DESTDIR)$(docdir)
	cp -a docs/html $(DESTDIR)$(htmldir)

unit-tests: force-rebuild
	make -C tests -s
	sh tests/run-tests.sh

lint: force-rebuild
	sh tests/run-pylint.sh $(PYLINT_ARGS) crash kdump

static-check: force-rebuild
	sh tests/run-static-checks.sh

ifneq ($(TESTS),)
TESTSARG=--tests $(TESTS)
endif

live-tests: force-rebuild
	sh tests/run-kernel-tests.sh $(TESTSARG) $(INI_FILES)

test: unit-tests static-check lint live-tests
	@echo -n

full-test: test doc

pycrash.1 : crash-python.1

%.1 : doc-source/%.rst doc-source/conf.py
	sphinx-build -a -b man doc-source .

%.1.gz : %.1
	$(GZIPCMD) -n -c $< > $@

prefix ?= /usr
mandir ?= $(prefix)/share/man
man1dir = $(mandir)/man1
GZ_MAN1 :=  pycrash.1.gz crash-python.1.gz

man: $(GZ_MAN1)

man-clean: FORCE
	rm -f $(GZ_MAN1)
	rm -f pycrash.1 crash-python.1

man-install: man
	$(INSTALL) -d -m 755 $(DESTDIR)$(man1dir)
	$(INSTALL) -m 644 $(GZ_MAN1) $(DESTDIR)$(man1dir)

gdb.inv:
	python3 doc-source/make_gdb_refs.py

doc-html: gdb.inv doc-source-clean
	sphinx-build -b html doc-source docs/html

doc-help: gdb.inv doc-source-clean
	sphinx-build -b text doc-source docs/text
	rm -f docs/text/commands/commands.txt

doc: doc-source-clean doc-html doc-help man FORCE

FORCE:
