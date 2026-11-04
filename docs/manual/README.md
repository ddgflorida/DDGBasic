# DbBasic Programmer's Reference Manual

DbBasic is a data-centric dialect of BASIC with built-in SQLite and DuckDB support. This manual describes the language as implemented in `src/dbbasic.py`. Each chapter was written from the interpreter source, and every example was run to confirm the output shown.

Where the code and the older documents (`README.md`, `docs/DbBasicCommandRerence.md`, `docs/DbBasicFunctionReference.md`, the built-in `HELP` text) disagree, this manual describes what the code **actually does**. It records each disagreement in the chapter's final *Implementation notes / discrepancies* section.

## Chapters

| # | Chapter | Covers |
|---|---------|--------|
| 1 | [Language Fundamentals](01-language-fundamentals.md) | Running programs, source format, comments, `INCLUDE`, line continuation, `ECHO`, the lexer, data types, variables, `LET`, `DIM`/`REDIM`, arrays, hashes, array statements (`PUSH`, `POP`, `SHIFT`, `UNSHIFT`, `SPLICE`, `REVERSE`, `SORT`), operators, truth values, case sensitivity |
| 2 | [Control Flow, Procedures & Program Control](02-control-flow-and-procedures.md) | `IF`, `FOR`/`NEXT`, the `FOR ... IN` family, `FOR EACH`, `WHILE`, `DO`/`LOOP`, `EXIT`, labels, `GOTO`, `GOSUB`, `FUNCTION`, functions as arguments, error handling (`ON ERROR`, `RESUME`, `ERROR`), `END`/`RUN`/`CHAIN`/`EVAL`/`EXECUTE`/`CLEAR`, debugging, command line, REPL and `HELP` |
| 3 | [Built-in Functions](03-built-in-functions.md) | All 122 built-in functions with an alphabetical index, `FORMAT$` masks, `FORMATDATE$` tokens, and the 15 extra functions available inside SQLite queries |
| 4 | [Database, SQL & Output](04-database-sql-and-output.md) | `DATABASE`, embedded SQL, bind variables, subqueries, `FOR row IN (SELECT ...)`, `EXECUTE`, `SHOW`/`DESCRIBE`, SQL errors, every `SET` option, the output pipeline and its 11 formats, SQLite vs DuckDB, `PRINT`, `PRINT USING`, `WRITE` |
| 5 | [Data Loading, Conversion & Analysis](05-data-loading-and-analysis.md) | `LOAD` (all 9 formats, destination modes, every `OPTIONS` key, `fields=`, transform/validate rules, `TRANSFORM`/`VALIDATE ... WITH`), `USING SCHEMA`, JSON/XML normalisation, file-to-file conversion, `PARSEJSON`, `FOR ... IN` file loops, `ANALYZE`, `UPGRADE` |
| 6 | [Files, System, Network & User Interface](06-files-system-network-ui.md) | Sequential file I/O, `FILES`, file and directory statements, `ZIP`/`UNZIP`/`UNPACK`, `SHELL`, `BROWSER`, `BELL`, `INPUT`, `FETCH`, `SET EMAIL`/`EMAIL`, TUI forms (`FORM`, `OPENFORM`, `GRIDEDIT`), the web runner |

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

Interactive scripts (forms, `GRIDEDIT`, `BROWSER`) are always skipped. Scripts that read `c:\ddg\...` data run only where that data exists.

## Requirements

Python 3.10+ with: `requests`, `duckdb`, `xlrd3`, `openpyxl`, `beautifulsoup4`, `xmltodict`, `pyarrow`.
Optional:
- `lxml`, for `STRIPHTML$` and `LOAD HTML`
- `textual`, for `OPENFORM` and `GRIDEDIT`

The web runner (`src/dbbasicweb.py`) imports `cgi`, so it needs Python 3.12 or earlier.

## Known issues at a glance

Fixed since the manual was first written: `INCLUDE`, `COPY ... AS`, `ZIP`, `UPGRADE JSON`, nested-loop skipping (`FOR EACH` inside `FOR`, `DO WHILE` inside `WHILE`, multiple `EXIT DO`), `EXIT FOR` followed by `NEXT var`, the function-reference list in compiled builds, the process exit status (now 1 after an untrapped error), and blank lines in `LOAD CSV`. These are marked *(fixed)* in the chapter notes.

The issues below were found while writing the manual. They are the most likely to catch you out; each chapter's final section has the full list.

**Fails outright**
- `PARSE JSON ... INTO` is not implemented; use `PARSEJSON()`. ([5.18](05-data-loading-and-analysis.md#518-implementation-notes--discrepancies))
- `END TRANSACTION;` is not recognised. ([4.14](04-database-sql-and-output.md#414-implementation-notes--discrepancies))

**Surprising behaviour**
- `'` is not a comment character. Use `REM` or `--`.
- Any line beginning with the letters `ECHO` is rewritten, so `echo_count = 5` breaks.
- Variable names are case-insensitive when read but case-sensitive when assigned.
- `SHIFT` and `UNSHIFT` operate on index 1; arrays from `ARRAY()`/`PUSH` start at 0.
- Common words are reserved and cannot be used as variable names: `user`, `size`, `type`, `title`, `label`, `message`, `source`, `text`, `body`, `host`, `port`.
- Any `identifier :` on a line is taken as a label, so `a = b : c = d` can fail with "Duplicate label".
- User-defined `FUNCTION`s are not available in the REPL or in `RUN`/`CHAIN` targets.

**SQL**
- The SQL line scanner stops at the first `;`, even inside a string literal.
- Multi-word keyword joining also alters SQL string literals: `'for each'` becomes `'FOREACH'`. The same happens to `TO FILE`, `WITH DETAILS` and similar pairs inside ordinary strings.
- `:name` inside literals and DuckDB `::TYPE` casts are treated as bind variables.
- `SET NULL_HANDLING` has no effect, and unknown `SET` options are not rejected.

**Functions**
- `CARDINAL$` and `ORDINAL$` (listed in `README.md`) do not exist.
- `DAYSINMONTH` takes `(month, year)`.
- `WEEKDAYNAME$(1)` is Monday, while `WEEKDAY` counts 1 as Sunday.
- `FORMAT$` has no `%` support.

**Example and test scripts**
- The scripts in `tests/` and `examples/` have been updated to current syntax and run cleanly. The exceptions:
  - `examples/analyzecsv.bas`, `loadexcelex.bas`, `loadtext.bas`, `npimonthly.bas` and `tests/loadexcel.bas` read data from `c:\ddg\...` paths that are not in the repository.
  - `examples/onerror.bas` ends with a deliberate fatal error.
  - `examples/loadjson.bas` and the form examples need an interactive terminal.
