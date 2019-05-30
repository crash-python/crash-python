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

all: man

man-install: man
	$(INSTALL) -d -m 755 $(DESTDIR)$(man1dir)
	$(INSTALL) -m 644 $(GZ_MAN1) $(DESTDIR)$(man1dir)

build: crash tests kernel-tests
	python3 setup.py -q build

install: man-install build
	python3 setup.py install

lint: lint3
	pylint --rcfile tests/pylintrc -r n crash

lint3:
	pylint --py3k -r n crash

doc: build FORCE
	rm -rf docs
	rm -f doc/source/crash.*rst doc/source/modules.rst
	python3 setup.py -q build_sphinx
FORCE:
