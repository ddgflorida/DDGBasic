#!/usr/bin/env python3
"""
Run the DbBasic test scripts and report PASS / FAIL / SKIP for each.

A script passes when it exits with status 0 (or with the status listed in
EXPECTED_EXIT) and its output contains the text of every 'REM EXPECT: text'
line in the script. Each script runs in its own fresh temporary copy of its
folder, so scripts that create or delete files can't disturb the repo or
each other.

Usage:
    python3 tests/run_tests.py                 # tests/ only, using src/dbbasic.py
    python3 tests/run_tests.py --examples      # tests/ and examples/
    python3 tests/run_tests.py --offline       # skip scripts that need the internet
    python3 tests/run_tests.py --binary        # use the compiled 'dbbasic' on PATH
    python3 tests/run_tests.py -v if while     # run only these scripts, show output

Exit status is 0 when nothing failed, 1 otherwise.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT_SECONDS = 120

# Scripts that need data files outside the repo; they run only where the file exists.
NEEDS_FILE = {
    'tests/loadexcel':          r'c:\ddg\data\excel\example.xlsx',
    'examples/analyzecsv':      r'c:\ddg\data\csv\raw_sales.csv',
    'examples/loadexcelex':     r'c:\ddg\data\excel\salesdata.xlsx',
    'examples/loadtext':        r'c:\ddg\data\csv\example.csv',
    'examples/npimonthly':      r'C:\DDG\NPI',
}

# Scripts that can't run unattended.
SKIP = {
    'examples/utils':           'subroutine library for INCLUDE, not a program',
    'examples/browser':         'opens a web browser',
}

# Scripts that download from the internet (skipped with --offline).
NETWORK = {
    'examples/convertcsv.io.fetch', 'examples/convertcsvio',
    'examples/govdomains', 'examples/govdomains_2',
    'examples/loadhtmltable', 'examples/loadhtmllink',
    'examples/loadhtmlimage', 'examples/npilinks',
}

# Scripts whose correct behaviour is a non-zero exit.
EXPECTED_EXIT = {
    'examples/onerror': 1,   # ends with a deliberate fatal division by zero
}

# Keyboard input fed to scripts that use INPUT.
STDIN = {
    'examples/loadjson': '\x1b[C\x1b[C\x1b[B60\r\x1b',   # BROWSE EDIT: Gadget quantity -> 60
    'examples/errorhandling': 'nope.txt\n\n',   # file-not-found path, then quit
    'examples/retro_contacts': ('\x1b[B\r'                          # Add a contact
                                'hooli\t5552223333\tca\t500\r' ' '  # fill in the form; a key for "Saved"
                                '\x1b[B\x1b[B\r' '\x1b[B\x1b[B\r'     # Edit: pick the 3rd row (HOOLI)
                                '\t\t\t750\r' ' '                    # change the credit
                                '\r' '\x1b'                         # Browse, then Esc
                                'q'),                               # Quit by its first letter
    'tests/file_io_fixes': 'Ann\nabc\n42\n',    # a name, then a bad and a good number
    'tests/browse_add_delete': ('\x1b[2~\t' 'pear\t4\r\x1b[C\r\x19Pear2\r\x1b[A\x1b[3~n\x1b[3~y\x1b[2~\x1b' '\x1b[2~\t\t1\r \x1b\x1b'            # SQLite
                                '\x1b[2~3\t' 'pear\t4\r\x1b[C\r\x19Pear2\r\x1b[A\x1b[3~n\x1b[3~y\x1b[2~\x1b' '\x1b[2~\t\t1\r \x1b\x1b'),         # DuckDB
    'tests/browse_edit': '\x1b[C\r\x19Apricot\r\x1b[C7\r-1\r\x1b[B\x1b[C\r\x19\r\x1b[D\x1b[DBanana2\t\x1b' '\r\x1b[CCherry\r\x1b' * 2,   # SQLite, then DuckDB
    'tests/edit_record': ('\x19jones\t\t\x19-5\r ' '\t\t\x1950\r' '\t\x19brown\tb@x.com\t7\r' '\x19zzz\x1b'     # SQLite
                          '\x19jones\t\t\x19-5\r ' '\t\t\x1950\r' '2\t\x19brown\tb@x.com\t7\r' '\x19zzz\x1b'),  # DuckDB
    'tests/auto_advance': 'ca01234\x1990210' '5551234567' 'xyz\tq\r',
    'tests/form_helpers': ('\x19x\r\x19b\r' 'zz\r\x1b[B\x1b[B\r' '9999\r\x194000\r' '\rAnn\r'
                           '\r\x1bOQ\x1b[B\r\r\r' '\x1b[C\r' '\r' 'c' '\x1b' '\r'),
    'tests/menubar': ('\r\x1b[B\r' '\x1b[C\r\x1b[B\x1b[B\r' '\r\x1b[C\x1b[C\r' 'ca' '\r\x1b[A\r'
                      '\x1b[C\r' '\r\x1b\x1b' '\r\r'),
    'tests/edit_text': ('\x1b[F ok\rthird\x1b[B\x1b[A\x1b[H\x1b[3~\x1b[3~\x17' 'zz\x1b\r\x19\x1b\x1b[C\r'
                        '\x19\x1b[21~' '\x1b[F\ty\x17' + 'abcdefghij' * 6 + '\x1b[H<\x17'),
    'tests/view': '\x1b[6~/total\rn\x1b[F\x1b' 'q' '\x1b' '\x1b',
    'tests/get_targets': '\x19jones\t\t900\r\x19250\r' '\x19uno\t\x19Austin\t02116\r' '\x19zzz\t\x19yyy\x1b',
    'tests/screen': ('ann smith\t5551234567\t-5\r\x1912\r'   # READ, with a VALID failure
                     'zzz\x1b'                               # READ cancelled with Esc
                     '\x1b[B\r' 'q'                          # two MENUs
                     '\x1b[B\x1b[B\r'                         # BROWSE
                     'k'),                                    # INKEY$
}


def expected_output(path):
    """Text from the script's 'REM EXPECT: text' lines, which must all appear in its output."""
    expected = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            stripped = line.strip()
            if stripped.upper().startswith('REM EXPECT:'):
                expected.append(stripped[len('REM EXPECT:'):].strip())
    return expected


def find_scripts(include_examples):
    dirs = ['tests'] + (['examples'] if include_examples else [])
    scripts = []
    for d in dirs:
        for name in sorted(os.listdir(os.path.join(REPO, d))):
            if name.lower().endswith('.bas'):
                scripts.append(f"{d}/{name[:-4]}")
    return scripts


def main():
    parser = argparse.ArgumentParser(description="Run the DbBasic test scripts.")
    parser.add_argument('names', nargs='*', help="only run scripts whose name matches (e.g. 'if' or 'examples/zip')")
    parser.add_argument('--examples', action='store_true', help="also run the scripts in examples/")
    parser.add_argument('--offline', action='store_true', help="skip scripts that need the internet")
    parser.add_argument('--binary', action='store_true', help="use the compiled 'dbbasic' on PATH instead of src/dbbasic.py")
    parser.add_argument('-v', '--verbose', action='store_true', help="print each script's full output")
    args = parser.parse_args()

    if args.binary:
        exe = shutil.which('dbbasic')
        if not exe:
            sys.exit("No 'dbbasic' executable found on PATH.")
        command = [exe]
    else:
        command = [sys.executable, os.path.join(REPO, 'src', 'dbbasic.py')]

    scripts = find_scripts(args.examples or any(n.startswith('examples/') for n in args.names))
    if args.names:
        wanted = {n[:-4] if n.lower().endswith('.bas') else n for n in args.names}
        scripts = [s for s in scripts if s in wanted or s.split('/')[1] in wanted]
        if not scripts:
            sys.exit(f"No scripts match: {' '.join(args.names)}")

    work = tempfile.mkdtemp(prefix='dbbasic-tests-')

    passed, failed, skipped = [], [], []
    try:
        for script in scripts:
            if script in SKIP:
                skipped.append(script)
                print(f"SKIP  {script:36} {SKIP[script]}")
                continue
            if script in NEEDS_FILE and not os.path.exists(NEEDS_FILE[script]):
                skipped.append(script)
                print(f"SKIP  {script:36} needs {NEEDS_FILE[script]}")
                continue
            if args.offline and script in NETWORK:
                skipped.append(script)
                print(f"SKIP  {script:36} needs the internet")
                continue

            folder, name = script.split('/')
            run_dir = os.path.join(work, script)
            shutil.copytree(os.path.join(REPO, folder), run_dir)
            started = time.time()
            try:
                result = subprocess.run(
                    command + [name + '.bas'],
                    cwd=run_dir,
                    input=STDIN.get(script, ''),
                    capture_output=True, text=True, errors='replace',
                    timeout=TIMEOUT_SECONDS)
                status, output = result.returncode, result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                status, output = None, f"(timed out after {TIMEOUT_SECONDS}s)"
            elapsed = time.time() - started

            expected = EXPECTED_EXIT.get(script, 0)
            missing = [text for text in expected_output(os.path.join(REPO, script + '.bas')) if text not in output]
            if status == expected and not missing:
                passed.append(script)
                print(f"PASS  {script:36} {elapsed:5.1f}s")
            else:
                failed.append(script)
                if status is None:
                    shown = 'timeout'
                elif status != expected:
                    shown = f"exit {status}, expected {expected}"
                else:
                    shown = 'missing expected output: ' + '; '.join(repr(text) for text in missing)
                print(f"FAIL  {script:36} {elapsed:5.1f}s  ({shown})")
                if not args.verbose:
                    for line in output.strip().splitlines()[-8:]:
                        print(f"      | {line}")
            if args.verbose:
                for line in output.rstrip().splitlines():
                    print(f"      | {line}")
            shutil.rmtree(run_dir, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(f"\n{len(passed)} passed, {len(failed)} failed, {len(skipped)} skipped")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
