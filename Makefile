ASCIIDOC = /usr/bin/asciidoc
ASCIIDOC_EXTRA =
MANPAGE_XSL = manpage-normal.xsl
XMLTO = /usr/bin/xmlto
XMLTO_EXTRA = -m manpage-bold-literal.xsl
GZIPCMD = /usr/bin/gzip
INSTALL = /usr/bin/install -c

MAN1_TXT = pycrash.asciidoc
prefix ?= /usr
mandir ?= $(prefix)/share/man
man1dir = $(mandir)/man1

GZ_MAN1 = $(patsubst %.asciidoc,%.1.gz,$(MAN1_TXT))

%.1.gz : %.1
	$(GZIPCMD) -n -c $< > $@

%.1 : %.xml
	$(RM) -f $@ && \
	$(XMLTO) -m $(MANPAGE_XSL) $(XMLTO_EXTRA) man $<

%.xml : %.asciidoc asciidoc.conf
	rm -f $@+ $@
	$(ASCIIDOC) -b docbook -d manpage -f asciidoc.conf \
		$(ASCIIDOC_EXTRA) -o $@+ $<
	mv $@+ $@

man: $(GZ_MAN1)

PYLINT_ARGS ?= --rcfile tests/pylintrc -r n

ifeq ($(E),1)
PYLINT_ARGS +=  -E
endif

all: man

man-install: man
	$(INSTALL) -d -m 755 $(DESTDIR)$(man1dir)
	$(INSTALL) -m 644 $(GZ_MAN1) $(DESTDIR)$(man1dir)

doc-clean:
	rm -rf docs
	rm -f doc-source/crash/*.rst doc-source/kdump/*.rst

clean: doc-clean
	make -C tests clean
	rm -rf build

build: crash tests
	python3 setup.py -q build

clean-build: clean build

install: man-install build
	python3 setup.py install

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

doc: build FORCE
	rm -rf docs
	rm -f doc-source/crash/.*rst doc-source/kdump/*.rst
	python3 setup.py -q build_sphinx
FORCE:
