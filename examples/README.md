# DbBasic examples

Run any of these with `dbbasic name.bas` from this folder (or `python3 ../src/dbbasic.py name.bas`), or open one in the IDE with `dbbasic --ide name.bas`. Most write any files they make into this folder. The test suite runs them all (`python3 tests/run_tests.py --examples`) except those that need files or an API token you won't have, or that open a browser.

## SQL and BASIC together

What DbBasic is for: SQL for the data, BASIC for the rules around it.

| Example | Shows |
|---|---|
| `etl_pipeline.bas` | A messy CSV to a clean table: `LOAD ... TRANSFORM/VALIDATE WITH` your own functions, duplicate and e-mail checks, customer tiers from a loop over a query, SQL totals, JSON, Excel and a `REPORT` |
| `duckdb_analytics.bas` | DuckDB on half a million rows: Parquet and CSV files queried directly, window functions, per-region targets in a hash, timings with `TIMER` |
| `two_engines.bas` | SQLite for the records (constraints, a transaction), DuckDB for the analysis (median, best month from a Parquet file), results back into SQLite |
| `row_logic.bas` | Allocating stock to orders by priority with all-or-nothing and partial rules, in a transaction rolled back by `ON ERROR` |
| `sqlex.bas` | Plain SQL: a table of countries and some queries |
| `govdomains.bas`, `govdomains_2.bas` | Download the list of .gov domains (`FETCH`), load it and query it (needs the internet) |
| `setoutputsql.bas` | DuckDB rows written out as SQL `INSERT` statements |

## Text-mode applications

1990s-style screens: forms, menus, grids and reports. See Chapter 7 of the manual.

| Example | Shows |
|---|---|
| `retro_contacts.bas` | A complete application: menu bar, editable grid with sorting and colours, entry forms with lists and hints, memo editor, report, F1 help |
| `invoice_demo.bas` | An invoice screen on the Chinook database (`data/chinook.sqlite`): header form, lines grid, PgUp/PgDn between invoices, business rules |
| `orders_demo.bas` | A master-detail screen (`BROWSE ... DETAIL`) with a business rule (`EDIT WHEN`) |
| `contact.bas` | The simplest useful form, saved with one `INSERT` |
| `form_demo.bas` | Every kind of entry field: pictures, dates, masks, check boxes, lists, lookups, buttons, F1 help |
| `grid_demo.bas` | `BROWSE` on 10,000 rows: sorting, type-ahead, frozen columns, formats, row colours, editing |
| `menu_demo.bas` | A menu bar, a pop-up menu and message boxes |
| `notes_demo.bas` | The memo editor (`EDIT TEXT`) and the viewer (`VIEW`) |
| `report_demo.bas` | `REPORT` with groups, totals and pages |
| `progress_demo.bas` | A progress bar and a menu longer than the screen |
| `themes_demo.bas` | The colour themes |
| `mouse_demo.bas` | A tiny paint program with the mouse |
| `make_form_demo.bas` | `MAKE FORM`: writes a whole data-entry program for a table |

## Loading and converting files

| Example | Shows |
|---|---|
| `loadcsv.bas`, `loadcsvnohead.bas`, `loadinto.bas` | `LOAD CSV` with and without headers, into new and existing tables |
| `csvconstraint.bas` | Checking values while loading (`REGEX`, digits, lengths) |
| `loadjson.bas` | `LOAD JSON` into DuckDB |
| `loadfixed.bas` | Fixed-width files |
| `loadtext.bas` | A text file, one line per row |
| `loadhtmltable.bas`, `loadhtmllink.bas`, `loadhtmlimage.bas` | Tables, links and images from a web page (need the internet) |
| `loadexcelex.bas` | An Excel workbook |
| `csv2json.bas`, `csv2jsonl.bas`, `csv2fixed.bas` | Converting a CSV file to JSON, JSON Lines and fixed-width |
| `convertcsvio.bas`, `convertcsv.io.fetch.bas` | Converting through the convertcsv.io web API (need an API token) |
| `analyzecsv.bas`, `npimonthly.bas`, `npilinks.bas` | `ANALYZE CSV` on large public files (need the files or the internet) |
| `json_serialize.bas`, `jsonserialize.bas` | Hashes and arrays to JSON |
| `write.bas`, `openfile.bas`, `name.bas` | Writing files, `OPEN`/`PRINT #`, file and folder statements |

## The language

| Example | Shows |
|---|---|
| `hello.bas` | Hello World |
| `functions.bas` | `FUNCTION`s: numbers and strings, several parameters, recursion |
| `strings.bas`, `dates.bas` | String and date functions |
| `doloop.bas`, `doloopbroke.bas` | `DO ... LOOP` forms |
| `for_in_hash.bas`, `hash_join.bas`, `sortex.bas` | Hashes and arrays: `FOR EACH`, `HASH_JOIN`, `SORT` |
| `errorhandling.bas`, `onerror.bas` | `ON ERROR GOTO`, `RESUME`, passing an error on |
| `continuation.bas` | Long statements over several lines with `_` |
| `browser.bas` | Opening a web page in the browser |
| `utils.bas` | A small library of subroutines for `INCLUDE` |
| `test.bas`, `test2.bas` | Small checks used while developing |

`data/` holds the Chinook sample database used by `invoice_demo.bas` (see `data/README.md`).
