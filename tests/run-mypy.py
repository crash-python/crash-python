# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import sys

print("Doing static checking.")

from mypy.main import main

common_args = ["--ignore-missing-imports",
               "--disallow-incomplete-defs",
               "--disallow-untyped-defs",
               "--disallow-untyped-calls",
               "--check-untyped-defs",
               "--disallow-untyped-globals"]

try:
    ret = main(None, stdout=sys.stdout, stderr=sys.stderr, args=["-p", "kdump"] + common_args)
    ret2 = main(None, stdout=sys.stdout, stderr=sys.stderr, args=["-p", "crash"] + common_args)
except TypeError:
    ret = main(None, args=["-p", "kdump"] + common_args)
    ret2 = main(None, args=["-p", "crash"] + common_args)

if ret or ret2:
    print("static checking failed.", file=sys.stderr)
    sys.exit(1)

print("OK")
sys.exit(0)
