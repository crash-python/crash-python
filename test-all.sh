#!/bin/sh

rm -rf build/lib/crash
python3 setup.py -q build
make -C tests -s
crash-python-gdb -nx -batch -ex "source tests/unittest-bootstrap.py"
 
has_mypy() {
	python3 -c 'import mypy' 2> /dev/null
}

if has_mypy; then
    cat <<- END > $DIR/gdbinit
	set build-id-verbose 0
	set python print-stack full
	set height 0
	set print pretty on
	python
	sys.path.insert(0, 'build/lib')
	from mypy.main import main
	main(None, args=["-p", "crash", "--ignore-missing-imports"])
	end
	END
    echo "Doing static checking."
    if ! crash-python-gdb -nx -batch -x $DIR/gdbinit; then
	echo "static checking failed." >&2
    else
	echo "OK"
    fi
fi
