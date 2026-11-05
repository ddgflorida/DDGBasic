# DbBasic Programmer's Reference Manual

DbBasic is a data-centric dialect of BASIC with built-in SQLite and DuckDB support. This manual describes the language as implemented in `src/dbbasic.py`. Each chapter was written from the interpreter source, and every example was run to confirm the output shown.

Where the code and the older documents (`README.md`, the original `docs/DbBasicCommandRerence.md` and `docs/DbBasicFunctionReference.md` quick references, now replaced by pointers to this manual, and the built-in `HELP` text) disagree, this manual describes what the code **actually does**. It records each disagreement in the chapter's final *Implementation notes / discrepancies* section.

## Chapters

| # | Chapter | Covers |
|---|---------|--------|
| 1 | [Language Fundamentals](01-language-fundamentals.md) | Running programs, source format, comments, `INCLUDE`, line continuation, `ECHO`, the lexer, data types, variables, `LET`, `DIM`/`REDIM`, arrays, hashes, array statements (`PUSH`, `POP`, `SHIFT`, `UNSHIFT`, `SPLICE`, `REVERSE`, `SORT`), operators, truth values, case sensitivity |
| 2 | [Control Flow, Procedures & Program Control](02-control-flow-and-procedures.md) | `IF`, `FOR`/`NEXT`, the `FOR ... IN` family, `FOR EACH`, `WHILE`, `DO`/`LOOP`, `EXIT`, labels, `GOTO`, `GOSUB`, `FUNCTION`, functions as arguments, error handling (`ON ERROR`, `RESUME`, `ERROR`), `END`/`RUN`/`CHAIN`/`EVAL`/`EXECUTE`/`CLEAR`, debugging, command line, REPL and `HELP` |
| 3 | [Built-in Functions](03-built-in-functions.md) | All 127 built-in functions with an alphabetical index, `FORMAT$` masks, `FORMATDATE$` tokens, and the 15 extra functions available inside SQL queries |
| 4 | [Database, SQL & Output](04-database-sql-and-output.md) | `DATABASE`, embedded SQL, bind variables, subqueries, `FOR row IN (SELECT ...)`, `EXECUTE`, `SHOW`/`DESCRIBE`, SQL errors, every `SET` option, the output pipeline and its 11 formats, SQLite vs DuckDB, `PRINT`, `PRINT USING`, `WRITE` |
| 5 | [Data Loading, Conversion & Analysis](05-data-loading-and-analysis.md) | `LOAD` (all 9 formats, destination modes, every `OPTIONS` key, `fields=`, transform/validate rules, `TRANSFORM`/`VALIDATE ... WITH`), `USING SCHEMA`, JSON/XML normalisation, file-to-file conversion, `PARSEJSON`, `FOR ... IN` file loops, `ANALYZE`, `UPGRADE` |
| 6 | [Files, System, Network & User Interface](06-files-system-network-ui.md) | Sequential file I/O, `FILES`, file and directory statements, `ZIP`/`UNZIP`/`UNPACK`, `SHELL`, `BROWSER`, `BELL`, `INPUT`, `FETCH`, `SET EMAIL`/`EMAIL`, 1990s-style text screens (`CLS`, `LOCATE`, `COLOR`, `BOX`, `@ SAY/GET`, `READ`, `MENU`, `BROWSE`, `INKEY$`), TUI forms (`FORM`, `OPENFORM`, `GRIDEDIT`) |

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

A script can also require output: it passes only if its output contains the text of each `REM EXPECT: text` line it contains. Interactive scripts (forms, `GRIDEDIT`, `BROWSER`) are always skipped. Scripts that read `c:\ddg\...` data run only where that data exists.

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
- `textual` (for terminal forms)

To build a standalone executable, install [`requirements-build.txt`](../../requirements-build.txt), which adds Nuitka, and run `compilenuitka.sh` or `compilenuitka.bat`.

## Known issues at a glance

Fixed since the manual was first written: `INCLUDE`, `COPY ... AS`, `ZIP`, `UPGRADE JSON`, nested-loop skipping (`FOR EACH` inside `FOR`, `DO WHILE` inside `WHILE`, multiple `EXIT DO`), `EXIT FOR` followed by `NEXT var`, the function-reference list in compiled builds, the process exit status (now 1 after an untrapped error), blank lines in `LOAD CSV`, `;` inside SQL string literals, keyword joining inside strings (`"TO FILE"` used to print as `TOFILE`), `END TRANSACTION;`, user-defined `FUNCTION`s in `RUN`/`CHAIN` targets, `EVAL` strings and the REPL, `ECHO` rewriting lines such as `echo_count = 5`, `PRINT #n, USING` crashing or writing no line ending, SQL operators such as `||` failing with `Unexpected character`, `:` inside SQL literals or DuckDB `::` casts being read as bind variables, and the function bugs: `CARDINAL$`/`ORDINAL$` missing, `WEEKDAYNAME$` off by one, `HOUR` of a datetime, `DAYSINMONTH` argument order, and `FORMAT$`/`PRINT USING` dropping `%` and trailing text. `SHIFT` and `UNSHIFT` now work on index 0, like every other array operation. `SET NULL_HANDLING` now works, and empty fields load as `NULL` by default. `KILL` of a missing file is now trapped by an active `ON ERROR` handler (it stays quiet without one). Labels are recognised only at the start of a line, so `a = b : c = d` no longer fails with "Duplicate label". Variable names are case-insensitive for assignment as well as reads (`Total` and `total` are one variable). `GOTO` out of a loop or block `IF` now ends the blocks it leaves. `END` in a `RUN` child returns to the caller instead of exiting the process. Unknown `SET` options are rejected, a successful `LOAD` resets `ERR`, `HELP` and `CHAIN` no longer print stray lines, and Ctrl-C stops a program cleanly (exit status 130). Comparisons work in assignments and `PRINT` (`x = a > b`), `.5` and `1e3` are valid numbers, and a SQL NULL in an expression acts as `""`. The experimental web runner has been removed from `main`; it is kept on the `experiment/web-runner` branch. `CREATE TRIGGER` can be written as line-level SQL and in `EXECUTE`. Function fixes: `RIGHT$(s, 0)`, negative `HEX$`/`OCT$`, date formats in `YEAR`/`DATEADD` and friends, `FORMATDATE$` masks, `.0` in `LEN`/`ARRAY_JOIN`/`FILTER`, `VAL` reading a leading number, standard `SOUNDEX$`, `HASH_DELETE`'s result, and clear errors for bad arguments. `UPGRADE CSV` accepts the schema saved by `ANALYZE CSV`. `.xlsx` and HTML loads work with `header=false`, nested Parquet columns keep their names, and `SET NULL_HANDLING` applies to `USING SCHEMA` and `normalize=true` loads too. DuckDB: the SQL helper functions are available, `SHOW INDEXES` works, `EXECUTE` displays query results, and JSON output handles dates and decimals. Output: `SET OUTPUT FORMAT TABLE`, HTML `full=false`, Excel titles, whole-number bind values, a trailing `,` in `PRINT`, and `PRINT USING` mask reuse. Files: clear errors for unopened handles, `ERR`/`ERRMSG$` from `OPEN`/`READ FILE`/`UNZIP`, `~` in all file names, matching `WRITE #` line endings, and `INPUT` with a comma and re-asking for numbers. Language: `SORT ... desc` in any case, `DIM x AS INTEGER`/`STRING`, negative array indexes rejected on write, `RUN` arguments without `.0`, and `RECNO` counting from 1 and surviving nested loops. ANALYZE: `INTO` without `DIM`, `HEADERS` as an array, multi-file XML `INTO`, either clause order for XML, JSONL non-object counts, and a runnable `ANALYZE FIXED` suggestion. LOAD: `INTO TABLE` defaults to `APPEND`, `IGNORE` reports the rows actually inserted, `validate=` names ignore case, `transform=` masks can contain `:`, XML `limit` stops reading, HTML links resolve against `source_url`, `fields=` warns where it is ignored, and `normalize=true` skips rows that fail validation (with their child rows), loads arrays of plain values without NULL rows, and counts only the tables it created. `ANALYZE JSON` accepts wildcards, and the built-in `HELP` for `IF`, `EXECUTE`, `RUN`, `CHAIN`, `EXIT`, `RESUME`, `FOR IN`, `SHOW CREATE TABLE`, `INSERT`, `UPDATE`, `ANALYZE JSON`, `LOAD JSON`/`FIXED`/`EXCEL` and `EMAIL` now matches the code. `PRINT x;` can be followed by `:` or `ELSE`, CSV rows with too few fields load with `NULL`s instead of aborting the load, a failed `CREATE TABLE` load drops its table, and delimiter sniffing only picks a comma, semicolon, tab or pipe. A `FOR ... IN JSONL` loop skips invalid lines with a warning instead of stopping. These are marked *(fixed)* or *(changed)* in the chapter notes.

The issues below were found while writing the manual. They are the most likely to catch you out; each chapter's final section has the full list.

**Surprising behaviour**
- `'` is not a comment character. Use `REM` or `--`.
- Common words are reserved and cannot be used as variable names: `user`, `size`, `type`, `title`, `label`, `message`, `source`, `text`, `body`, `host`, `port`.
- JSON is parsed with the `PARSEJSON()` function; there is no `PARSE JSON ... INTO` statement.

**SQL**
- `LOAD` stores empty fields (including all-space fields) as `NULL` by default. Use `SET NULL_HANDLING TO EMPTY` to keep `''`.

**Example and test scripts**
- The scripts in `tests/` and `examples/` have been updated to current syntax and run cleanly. The exceptions:
  - `examples/analyzecsv.bas`, `loadexcelex.bas`, `loadtext.bas`, `npimonthly.bas` and `tests/loadexcel.bas` read data from `c:\ddg\...` paths that are not in the repository.
  - `examples/onerror.bas` ends with a deliberate fatal error, after its handler has trapped a `KILL` of a missing file.
  - `examples/loadjson.bas` and the form examples need an interactive terminal.
