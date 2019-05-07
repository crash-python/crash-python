#!/bin/sh

set -e

cleanup() {
    test -n "$DIR" && rm -rf "$DIR"
}

trap cleanup EXIT

DIR=$(mktemp -d "/tmp/crash-python-tests.XXXXXX")

export CRASH_PYTHON_TESTDIR="$DIR"

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

cat << END > $DIR/gdbinit
python sys.path.insert(0, 'build/lib')
set build-id-verbose 0
set python print-stack full
set prompt py-crash> 
set height 0
set print pretty on
source kernel-tests/unittest-prepare.py
source kernel-tests/unittest-bootstrap.py
END

for f in "$@"; do
    export CRASH_PYTHON_TESTFILE="$f"
    crash-python-gdb -nx -batch -x $DIR/gdbinit
done
