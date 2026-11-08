"""Checks that Interpreter.BUILTIN_FN_NAMES in src/ddgbasic.py lists every built-in function.

A compiled (Nuitka) build can't read its own source, so it relies on that list for function
references (FILTER, MAP, REDUCE, SORT WITH). The build scripts run this first and stop if the
list is out of date. Exit status 0 means the list is current.
"""
import inspect
import os
import re
import sys

src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, os.path.normpath(src))
sys.argv = ['ddgbasic']
import ddgbasic  # noqa: E402

code = inspect.getsource(ddgbasic.Interpreter._execute_function)
actual = set(re.findall(r"name == '([A-Z_][A-Z_0-9]*\$?)'", code))
listed = set(ddgbasic.Interpreter.BUILTIN_FN_NAMES)
if actual != listed:
    print("BUILTIN_FN_NAMES in src/ddgbasic.py is out of date.", file=sys.stderr)
    print("  missing:", sorted(actual - listed), file=sys.stderr)
    print("  extra:  ", sorted(listed - actual), file=sys.stderr)
    sys.exit(1)
