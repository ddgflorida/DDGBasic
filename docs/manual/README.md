# DbBasic Programmer's Reference Manual

DbBasic wraps a procedural language around SQLite and DuckDB: SQL is written straight into the program, query results come back as rows to loop over, and program variables go into queries as bind variables. The language around the SQL is a modern BASIC. This manual describes the language as implemented in `src/dbbasic.py`. Each chapter was written from the interpreter source, and every example was run to confirm the output shown. Each chapter ends with a *Notes* section of details that are easy to miss.

## Chapters

| # | Chapter | Covers |
|---|---------|--------|
| 1 | [Language Fundamentals](01-language-fundamentals.md) | Running programs, source format, comments, `INCLUDE`, line continuation, `ECHO`, the lexer, data types, variables, `LET`, `DIM`/`REDIM`, arrays, hashes, array statements (`PUSH`, `POP`, `SHIFT`, `UNSHIFT`, `SPLICE`, `REVERSE`, `SORT`), operators, truth values, case sensitivity |
| 2 | [Control Flow, Procedures & Program Control](02-control-flow-and-procedures.md) | `IF`, `FOR`/`NEXT`, the `FOR ... IN` family, `FOR EACH`, `WHILE`, `DO`/`LOOP`, `EXIT`, labels, `GOTO`, `GOSUB`, `FUNCTION`, functions as arguments, error handling (`ON ERROR`, `RESUME`, `ERROR`), `END`/`RUN`/`CHAIN`/`EVAL`/`EXECUTE`/`CLEAR`, debugging, command line, REPL, the IDE (`dbbasic --ide`) and `HELP` |
| 3 | [Built-in Functions](03-built-in-functions.md) | All 134 built-in functions with an alphabetical index, `FORMAT$` masks, `FORMATDATE$` tokens, and the 15 extra functions available inside SQL queries |
| 4 | [Database, SQL & Output](04-database-sql-and-output.md) | `DATABASE`, embedded SQL, bind variables, subqueries, `FOR row IN (SELECT ...)`, `EXECUTE`, `SHOW`/`DESCRIBE`, SQL errors, every `SET` option, the output pipeline and its 11 formats, SQLite vs DuckDB, `PRINT`, `PRINT USING`, `WRITE`, `REPORT` (grouped reports with subtotals, totals and pages) |
| 5 | [Data Loading, Conversion & Analysis](05-data-loading-and-analysis.md) | `LOAD` (all 9 formats, destination modes, every `OPTIONS` key, `fields=`, transform/validate rules, `TRANSFORM`/`VALIDATE ... WITH`), `USING SCHEMA`, JSON/XML normalisation, file-to-file conversion, `PARSEJSON`, `FOR ... IN` file loops, `ANALYZE`, `UPGRADE` |
| 6 | [Files, System, Network & User Interface](06-files-system-network-ui.md) | Sequential file I/O, `FILES`, file and directory statements, `ZIP`/`UNZIP`/`UNPACK`, `SHELL`, `BROWSER`, `BELL`, `INPUT`, `FETCH`, `SET EMAIL`/`EMAIL` |
| 7 | [Text-mode Applications](07-text-mode-applications.md) | A tutorial (a contact manager), then `CLS`, `LOCATE`, `COLOR`, `BOX`, `SAVESCREEN`/`RESTSCREEN`, `@ ... SAY ... GET` with `PICTURE`, `VALID ... MESSAGE`, `WHEN` and `LOOKUP`, `READ`, `MENUBAR$`, `MENU`, `ALERT`, `BROWSE` (with `EDIT`), `EDIT RECORD`, `EDIT TEXT`, `VIEW`, `INKEY$`/`LASTKEY$`, `ON KEY`, the mouse, `MAKE FORM` and master-detail screens |

## Quick start

```basic
DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"

LOAD CSV "sales.csv" CREATE TABLE sales OPTIONS "header=true"

FOR row IN (SELECT region, SUM(amount) AS total FROM sales GROUP BY region)
    PRINT row.region; ": "; FORMAT$(row.total, "$#,##0.00")
NEXT
```

To run a script:

```bash
python3 src/dbbasic.py script.bas [args...]   # from source
dbbasic script.bas [args...]                  # compiled build (see compilenuitka.sh)
```

Running with no script starts the interactive REPL. Type `HELP` there for the built-in help topics. See [2.17 Running DbBasic](02-control-flow-and-procedures.md#217-running-dbbasic).

## Running the tests

`tests/run_tests.py` runs each test script in its own temporary copy of its folder and reports PASS, FAIL or SKIP. A script passes when it exits with status 0; untrapped runtime errors exit with 1. The runner itself exits with 1 if anything failed.

```bash
python3 tests/run_tests.py                       # tests/ with src/dbbasic.py
python3 tests/run_tests.py --examples            # also examples/
python3 tests/run_tests.py --examples --offline  # skip scripts that download data
python3 tests/run_tests.py --binary              # test the compiled dbbasic on PATH
python3 tests/run_tests.py -v while zip          # selected scripts, full output
```

A script can also require output: it passes only if its output contains the text of each `REM EXPECT: text` line it contains. Scripts that open a web browser are always skipped; text-screen scripts get scripted keystrokes from the runner. Scripts that read `c:\ddg\...` data run only where that data exists.

## Requirements

Python 3.10 or newer. Install the dependencies with:

```bash
pip install -r requirements.txt
```

[`requirements.txt`](../../requirements.txt) lists each package with the features it is used for:

- `requests`
- `duckdb`
- `xlrd3`
- `openpyxl`
- `beautifulsoup4`
- `lxml`
- `xmltodict`
- `pyarrow`

To build a standalone executable, install [`requirements-build.txt`](../../requirements-build.txt), which adds Nuitka, and run `compilenuitka.sh` or `compilenuitka.bat`.

## Things to know

A few details are the most likely to catch you out; each chapter's *Notes* section has the full list.

**Surprising behaviour**
- `'` is not a comment character. Use `REM` or `--`.
- JSON is parsed with the `PARSEJSON()` function; there is no `PARSE JSON ... INTO` statement.

**SQL**
- `LOAD` stores empty fields (including all-space fields) as `NULL` by default. Use `SET NULL_HANDLING TO EMPTY` to keep `''`.

**Example and test scripts**
- The scripts in `tests/` and `examples/` run cleanly with the test runner. The exceptions:
  - `examples/analyzecsv.bas`, `loadexcelex.bas`, `loadtext.bas`, `npimonthly.bas` and `tests/loadexcel.bas` read data from `c:\ddg\...` paths that are not in the repository.
  - `examples/onerror.bas` ends with a deliberate fatal error, after its handler has trapped a `KILL` of a missing file.
  - `examples/loadjson.bas` and the text-screen examples are meant for an interactive terminal; the test runner plays them with scripted keystrokes.
