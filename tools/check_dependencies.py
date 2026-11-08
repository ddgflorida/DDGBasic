"""Checks that this Python has the DuckDB and numpy versions DDGBasic needs.

A compiled (Nuitka) build bundles the DuckDB it finds, so the build scripts run this first
and stop rather than build a program with a DuckDB that is too old. Exit status 0 means fine.
"""
import os
import sys

src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, os.path.normpath(src))
sys.argv = ['ddgbasic']
import ddgbasic  # noqa: E402

problem = ddgbasic.duckdb_problem()
if problem:
    print(problem, file=sys.stderr)
    print("Then run the build again.", file=sys.stderr)
    sys.exit(1)
