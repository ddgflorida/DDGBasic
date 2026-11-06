# DbBasic: A Data-Centric BASIC Interpreter and Procedural Language for SQLite and DuckDB

![Language](https://img.shields.io/badge/language-BASIC-blue.svg)
![Backend](https://img.shields.io/badge/backend-Python-green.svg)
![Status](https://img.shields.io/badge/status-Active-brightgreen.svg)

DbBasic is a custom, modern dialect of the BASIC programming language, built from the ground up in Python. It is designed with a strong focus on data processing, file manipulation, and direct database interaction, making it a powerful tool for scripting and data analysis tasks.
You can think of it as either SQLite/DuckDb wrapped in a procedural language, or a BASIC with direct SQLite/DuckDb support.

---

## ✨ Key Features

DbBasic combines the simplicity of classic BASIC syntax with powerful, modern features for today's data-driven world.

* ### Dual Database Engines
    * **SQLite & DuckDB Support:** Seamlessly switch between the world's most deployed database engine (**SQLite**) for general-purpose tasks and a high-performance analytical engine (**DuckDB**) for complex queries.
    * **SQL:** Directly embed SQL statements, iterate over resultsets.
    * **Engine Switching:** Use the `DATABASE ENGINE [SQLITE|DUCKDB]` command to change the backend at any time within a script.

* ### Powerful Data Ingestion & Transformation
    * **`LOAD` Command:** Ingest data from `.csv`, fixed-width, `.json`, `.jsonl`, `.xml`, `.parquet`, `.html`, and `.xls`/`.xlsx` (**Excel**) files into database tables or for file-to-file conversion.
    * **First-class TRANSFORM and VALIDATE clauses:** Apply user-defined functions (UDFs) or built-ins per cell or per row during loading: `LOAD CSV "raw.csv" CREATE TABLE clean TRANSFORM phone WITH normalize_phone$ VALIDATE email WITH is_valid_email TRANSFORM ROW WITH derive_full_name`.
    * **OPTIONS string:** Headers, delimiters, encoding, and the legacy transform/validate rules (upper, lower, trim, REQUIRED, MINLENGTH, REGEX).
    * **Field manipulation:** Select, rename (`fields=[Name] as N`), and exclude (`fields=*,-[Name]`) columns on the fly during data loading.

* ### User-Defined Functions
    * **`FUNCTION ... END FUNCTION`:** Define your own functions with parameters and return values.
    * **Local scope:** Parameters are local by shadow. Use `DIM` inside a function body to declare additional locals — outer same-named variables are preserved across the call.
    * **Recursion:** Functions can call themselves; recursion is safe when locals are declared via `DIM`.
    * **Early return:** `EXIT FUNCTION` returns immediately.
    * **Call as statement or expression:** `log_event("started")` discards the return; `score = lead_score(row)` uses it.

* ### Higher-Order Functions
    * **`FILTER`, `MAP`, `REDUCE`** accept either a UDF or a built-in by name: `MAP(words, UCASE$)`, `REDUCE(nums, MAX)`, `FILTER(leads, is_qualified)`.
    * **`SORT array WITH fn`:** Sort by a function-computed key — `SORT names WITH UCASE$ ASC` for case-insensitive sort, or use a UDF for composite/numeric/custom keys.
    * **Composition:** Pipelines like `REDUCE(MAP(FILTER(nums, is_even), square), add, 0)` work cleanly.

* ### 1990s-Style Text Screens
    * Blue screens, boxes and data-entry forms the way they used to be: `CLS`, `COLOR 15, 1`, `BOX`, `@ 5, 10 SAY "Name: " GET name$ PICTURE "@!" VALID name$ <> ""`, `READ`, light-bar `MENU()` and a scrolling `BROWSE (SELECT ...)` that can edit cells in place (`EDIT`). Keyboard and mouse. No extra packages. See `examples/retro_contacts.bas`, and the short `contact`, `form_demo`, `menu_demo`, `grid_demo`, `orders_demo`, `progress_demo`, `report_demo`, `notes_demo` and `mouse_demo` examples.

* ### String Interpolation
    * Backtick-delimited strings (`` ` ``) support `${expr}` interpolation: `` `Hello, ${name$}! Total: ${FORMAT$(amount, "$#,##0.00")}` ``.
    * Full expressions allowed inside `${...}` — including UDF calls, hash lookups, arithmetic.
    * Lone `{` and `}` remain literal (so JSON, code snippets, and regex survive intact).
    * `$$` produces a literal `$`. Double-quoted strings are unaffected (no interpolation).

* ### Modern Connectivity & Tooling
    * **`FETCH` Command:** HTTP `GET`/`POST`/`PUT`/`PATCH`/`DELETE`. Send a hash as the body, attach custom request headers, upload files (multipart), capture the response into a variable or file, and optionally capture response headers as a hash.
    * **`SHELL` Command:** Execute shell commands directly from the script.
    * **Data Analysis:** `ANALYZE [CSV|JSON|JSONL|FIXED|TEXT|XML]` commands provide detailed statistical reports and schema information about local files.
    * **Format Conversion:** `LOAD` combined with `SET OUTPUT FORMAT [format]` and a `SELECT` statement converts files between formats.

* ### Rich Language & SQL Integration
    * **Full control flow:** `IF...THEN...ELSE...END IF`, `FOR...TO...NEXT`, `WHILE...WEND`, `DO...LOOP`, `FOR EACH`.
    * **Row-streaming `FOR ... IN`:** Iterate over CSV, JSON, JSONL, files, text lines, or a SQL result set — `FOR row IN (SELECT * FROM sales) ... NEXT`.
    * **`EXIT` statements:** Reliably exit any loop (`EXIT FOR`, `EXIT WHILE`, `EXIT DO`), even from within nested blocks.
    * **Direct SQL execution:** Run any SQL query directly. Supports transactions (`BEGIN`, `COMMIT`, `ROLLBACK`) and logical checks like `IF EXISTS (...)`.
    * **Embedded subqueries:** Use scalar SQL subqueries directly in assignment statements: `LET count = (SELECT COUNT(*) FROM my_table;)`.
    * **Modern data types:** `HASH` (dictionary) and dynamic `ARRAY`, with a rich library of built-in functions.

---

## 📦 Installation

DbBasic needs Python 3.10 or newer.

```bash
pip install -r requirements.txt
python3 src/dbbasic.py examples/hello.bas      # run a script
python3 src/dbbasic.py                         # interactive REPL
```

To build a standalone executable, install `requirements-build.txt` and run `./compilenuitka.sh` (macOS/Linux; installs to `~/.local/bin`) or `compilenuitka.bat` (Windows; installs to `c:\ddg\bin`). Both build `src/dbbasic.py` from any folder and take another install folder as an argument, for example `compilenuitka.bat d:\tools`.

The full **Programmer's Reference Manual** is in [`docs/manual/`](docs/manual/README.md). Run the test suite with `python3 tests/run_tests.py`.

---

## 🚀 Quick Start Example

The following DbBasic script demonstrates several key features: it downloads a CSV file, loads it into a DuckDB in-memory table, and queries the result.

```basic
REM --- Set engine to DuckDB for high-speed analytics ---
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"

REM --- Download a CSV and create a table from it in one command ---
PRINT "Fetching and loading data..."
CREATE TABLE domains AS
  SELECT * FROM read_csv_auto('https://raw.githubusercontent.com/cisagov/dotgov-data/main/current-full.csv');

REM --- Run a query on the loaded data ---
PRINT "Top 5 States with the most .gov domains:"
SELECT State, COUNT(*) AS DomainCount
FROM domains
GROUP BY State
ORDER BY DomainCount DESC
LIMIT 5;

DATABASE CLOSE
END
```

---

## 🧩 ETL Pipeline Example

This shows the declarative ETL style enabled by UDFs and first-class TRANSFORM/VALIDATE clauses.

```basic
FUNCTION normalize_phone$(p$)
  DIM digits$
  digits$ = ""
  FOR i = 1 TO LEN(p$)
    c$ = MID$(p$, i, 1)
    IF ISDIGIT(c$) THEN digits$ = digits$ & c$
  NEXT
  IF LEN(digits$) = 11 AND LEFT$(digits$, 1) = "1" THEN digits$ = MID$(digits$, 2, 10)
  IF LEN(digits$) = 10 THEN
    normalize_phone$ = "(" & LEFT$(digits$,3) & ") " & MID$(digits$,4,3) & "-" & RIGHT$(digits$,4)
  ELSE
    normalize_phone$ = ""
  END IF
END FUNCTION

FUNCTION is_valid_email(addr$)
  is_valid_email = 0
  at_pos = INSTR(addr$, "@")
  IF at_pos < 2 THEN EXIT FUNCTION
  IF INSTR(MID$(addr$, at_pos+1, LEN(addr$)), ".") = 0 THEN EXIT FUNCTION
  is_valid_email = -1
END FUNCTION

DATABASE ENGINE SQLITE
DATABASE OPEN "leads.sqlite"

LOAD CSV "raw_leads.csv" CREATE TABLE leads _
  OPTIONS "header=true" _
  TRANSFORM name  WITH PROPER$ _
  TRANSFORM phone WITH normalize_phone$ _
  VALIDATE  email WITH is_valid_email

PRINT `Imported ${(SELECT COUNT(*) FROM leads;)} clean rows.`
```

---

## 📜 Statements Reference

A summary. The [Programmer's Reference Manual](docs/manual/README.md) has the full syntax, options and examples for every statement and function.

| Statement Keyword        | Description                                             |
|-------------------------|--------------------------------------------------------|
| @ ... SAY ... GET        | Writes text at a screen position (`SAY`) and adds an entry field (`GET`) for a variable, a hash field such as `rec.name`, or an array element, with optional `PICTURE`, `VALID ... MESSAGE`, `WHEN` and `LOOKUP (SELECT ...)` clauses, date fields (`@D`), numeric masks, `CHECKBOX` and drop-down `LIST` fields, and `HINT` help lines. See `READ`. |
| @ ... BUTTON            | Adds a `[ label ]` button to a form; pressing it ends `READ`, and `BUTTON$` returns its label (`CANCEL` buttons put the old values back). |
| ANALYZE CSV             | Provides a detailed statistical report on a CSV file, including delimiter detection, header presence, and column data types. |
| ANALYZE FIXED           | Analyzes a fixed-width text file, automatically guessing column breaks if not specified, and reports on the layout. |
| ANALYZE JSON            | Analyzes a JSON file, reporting on its structure, record count, and the consistency of object keys. |
| ANALYZE JSONL           | Analyzes a JSON Lines file, reporting on structural consistency, and counting valid and invalid JSON objects. |
| ANALYZE TEXT            | Provides a statistical analysis of a plain text file, including character, word, and line counts, encoding, and newline style. |
| ANALYZE XML             | Analyzes an XML file to determine its structure, infer the primary record tag, and list its fields. |
| BELL                    | Emits an audible system beep sound. |
| BOX                     | Draws a single- or double-line box with an optional title and `SHADOW` on the text screen. Pop-ups have drop shadows unless `SET SHADOW OFF`. |
| BROWSE                  | Shows query results in a scrolling grid; `INTO var` receives the chosen row as a hash. With `EDIT`, cells are edited in place and saved to the table, Ins adds a row and Del deletes one. Click a heading (or F3) to sort, type to jump to a row; `FREEZE`, `FORMAT` and `COLOR` set frozen columns, number masks and row colours. `DETAIL` adds a second grid for the rows of the current one (an order's lines). |
| BROWSER                 | Opens a specified URL in the system's default web browser. |
| CHAIN                   | Transfers program execution to a different DbBasic script, optionally preserving variables. |
| CHDIR                   | Changes the current working directory. |
| CLEAR                   | Deletes all variables. User-defined functions stay defined. |
| CLOSE                   | Closes a specific file handle or all open file handles. |
| CLS                     | Clears the screen in the current colours. |
| COLOR                   | Sets the text colours (0-15) and the colours of entry fields and menu bars. |
| COPY ... AS             | Copies a source file to a destination file. |
| DATABASE                | Manages the database connection, allowing you to open a file-based database or switch the database engine (SQLite/DuckDB). |
| DESCRIBE                | Lists a table's columns and types. Use `SHOW CREATE TABLE` for the CREATE TABLE statement. |
| DIM                     | Declares a variable (scalar, ARRAY, or HASH). When used inside a FUNCTION body, the declared name is scoped to the function and the outer variable of the same name is preserved across the call. |
| DO ... LOOP             | Defines a block of code that executes repeatedly, with optional WHILE or UNTIL conditions at the beginning or end. |
| DUMP                    | A debugging command to print the internal state of the interpreter, such as tokens, variables, or labels. |
| EDIT RECORD             | A one-line entry form: one labelled field per column of a query's row, saved with UPDATE (or INSERT when there is no row). |
| EDIT TEXT               | A boxed memo editor for a multi-line string (a variable or a field such as `rec.notes`); Ctrl-W saves, Esc cancels. |
| EMAIL                   | Sends an email using the configured provider (see `HELP SET EMAIL`), with support for HTML body, CC/BCC, and attachments. |
| END                     | Terminates the program execution. |
| ERROR                   | Triggers a user-defined runtime error with a specific error code and optional message. |
| EVAL                    | Executes a DbBasic source string as code. |
| EXECUTE                 | Executes a SQL statement that is dynamically constructed in a string variable. |
| EXIT                    | Immediately exits the current loop structure (`EXIT FOR`, `EXIT DO`, `EXIT WHILE`) or function (`EXIT FUNCTION`). |
| FETCH                   | Performs an HTTP request (GET, POST, PUT, PATCH, or DELETE). Supports request body hashes, custom request headers, multipart file uploads, INTO var$ or TO FILE destinations, and optional `HEADERS INTO h` capture of response headers. |
| FILES                   | Lists files and directories in the filesystem, similar to DIR or ls, with options for recursion and details. |
| FOR ... NEXT            | Iterates a set number of times, over the results of a SQL query, or through records in a CSV, JSON, JSONL, TEXT, or FILES list. |
| FOR EACH ... NEXT       | Iterates over each key in a HASH variable. |
| FUNCTION ... END FUNCTION | Defines a user-defined function. Parameters are local (shadow outer same-named variables). Use `DIM` inside the body for additional locals. The function returns the value of its own name. `EXIT FUNCTION` returns early. |
| GOSUB ... RETURN        | Jumps to a labeled subroutine and returns to the next statement after the GOSUB call. |
| GOTO                    | Unconditionally jumps program execution to a specified label. |
| HELP                    | Help system when running in interactive mode. |
| IF ... THEN ... ELSE ... END IF | Executes blocks of code conditionally. |
| INPUT                   | Prompts the user for input from the console and stores it in a variable. |
| KILL                    | Deletes a file from the filesystem. |
| LET                     | Assigns a value to a variable (the LET keyword is optional). |
| LINE INPUT              | Reads a single line of text from an open file into a variable. |
| LOAD                    | Loads data from a file (CSV, JSON, JSONL, XML, HTML, FIXED, EXCEL, PARQUET, TEXT) into a database table. Supports first-class `TRANSFORM col WITH fn`, `VALIDATE col WITH fn`, `TRANSFORM ROW WITH fn`, `VALIDATE ROW WITH fn` clauses. |
| LOCATE                  | Moves the cursor to a row and column. |
| MAKE FORM               | Writes a complete data-entry program for a table: menu bar, editable grid, and an entry form with fields chosen from the column types (dates, number masks, check boxes, drop-downs for foreign keys). |
| MKDIR                   | Creates a new directory. |
| NAME ... AS             | Renames a file. |
| ON ERROR GOTO           | Specifies a label to jump to when a runtime error occurs. |
| ON KEY                  | Makes a key (F1, CTRL-S, ALT-H, ...) run a FUNCTION whenever the program waits for a key, in any form, grid or menu. |
| OPEN                    | Opens a file for reading, writing, or appending, assigning it a file handle. |
| POP                     | Removes the last element from an array, optionally storing it in a variable. |
| PRINT                   | Outputs text, variables, or expressions to the console or an open file. |
| PROGRESS                | Shows a centred box with a progress bar and percentage for a long job; `PROGRESS OFF` removes it. |
| PUSH                    | Adds a new element to the end of an array. |
| READ                    | Edits the pending `@ ... GET` fields; Esc restores the original values. |
| REPORT                  | Turns a query into a report with a title, group headings, subtotals, totals and pages, to the screen, a file, `VIEW` or a string. |
| RESTSCREEN              | Puts back a screen area saved with `SAVESCREEN()`. |
| READ FILE               | Reads the entire content of a text file into a single string variable. |
| REDIM                   | Resizes a previously declared ARRAY. |
| RESUME                  | Used within an error-handling routine to resume program execution at the statement after the one that caused the error. |
| REVERSE                 | Reverses the order of elements in an array. |
| RMDIR                   | Removes an empty directory. |
| RUN                     | Executes another DbBasic script as a subroutine and returns control to the calling script upon completion. |
| SET                     | Configures global settings for the interpreter, such as OUTPUT redirection, output FORMAT, EMAIL provider, SQL_FATAL_ERRORS, or HASH_KEYS handling. |
| SHELL                   | Executes a command in the underlying operating system shell. |
| SHIFT                   | Removes the first element from an array, optionally storing it in a variable. |
| SHOW                    | Displays database schema information, such as `SHOW TABLES` or `SHOW INDEXES`. Also `SHOW VARIABLES`. |
| SORT                    | Sorts an array in-place. Use `ON "key"` to sort an array of hashes by a key. Use `WITH fn` to sort by a function-computed key (UDF or built-in). Optional `ASC` / `DESC`. |
| SPLICE                  | Modifies an array by removing, replacing, and/or adding elements at a specific index. |
| SQL Statement           | Any line starting with a SQL keyword (e.g., SELECT, INSERT, UPDATE) is executed directly against the current database. Must end in semi-colon. |
| TROFF                   | Turns off (Trace Off) the line-by-line execution trace. |
| TRON                    | Turns on (Trace On) a line-by-line execution trace for debugging. |
| UNSHIFT                 | Adds a new element to the beginning of an array. |
| UNZIP                   | Extracts files from a zip archive into a specified directory. |
| VIEW                    | Shows a file (`VIEW FILE`), a query or a string in a read-only, scrolling box with search (`/`, `n`). |
| WHILE ... WEND          | Executes a block of code as long as a specified condition is true. |
| WRITE                   | Writes a comma-separated list of expressions to the console or a file, automatically quoting strings. |
| ZIP                     | Creates a zip archive from a list of specified files. |

---

# DbBasic Interpreter: Functions

This document provides a quick reference to all available functions in the DbBasic language, categorized by function type.

| Function Name            | Type        | Description |
|-------------------------|-------------|-------------|
| ABS(number)             | MATH        | Returns the absolute value of a number. |
| ALERT(message$, [button$, ...]) | SCREEN | Shows a message box with buttons and returns the chosen button number (0 for Esc). |
| ARRAY(...)              | ARRAY       | A constructor that creates and returns a new ARRAY from the provided arguments. |
| ARRAY_JOIN(array, [delimiter$]) | ARRAY  | Concatenates the elements of an array into a single string, separated by delimiter$ (default comma). |
| ARRAY_SIZE(array)       | ARRAY       | Returns the total number of elements in an array. |
| ASC(string$)            | STRING      | Returns the ASCII code of the first character in the string. |
| ATN(number)             | MATH        | Returns the arctangent of a number in radians. |
| ATAN2(y, x)             | MATH        | Returns the arctangent of y/x in radians. |
| BASENAME$(path$)        | FILE        | Returns the filename portion of a path. |
| BUTTON$                 | SCREEN      | The label of the button that ended the last `READ` ("" if none). |
| CARDINAL$(number)       | STRING      | Returns the English cardinal words for a number (e.g. 12 → "twelve", 1234 → "one thousand two hundred thirty-four"). Negative numbers prefix "negative". Decimals are spelled digit-by-digit after "point". |
| CEIL(number)            | MATH        | Rounds a number up to the nearest integer. |
| CENTER$(string$, width, [pad_char$]) | STRING | Centers a string within a field of the given width, padded with pad_char$ (default space). |
| CHR$(code)              | STRING      | Returns the character corresponding to the given ASCII code. |
| COMMAND$(index)         | INFO        | Returns the command-line argument at the specified index position. |
| CONTAINS(string$, substring$) | STRING | Returns true (-1) if string$ contains substring$, otherwise false (0). |
| COS(number)             | MATH        | Returns the cosine of an angle given in radians. |
| CURDIR$()               | FILE        | Returns the current working directory as a string. |
| DATE$()                 | DATE/TIME   | Returns the current system date as a "YYYY-MM-DD" string. |
| DATEADD(date$, days)    | DATE/TIME   | Adds a specified number of days to a date$ and returns the new date string. |
| DATEDIFF(date1$, date2$)| DATE/TIME   | Returns the number of days between two date strings. |
| DATESERIAL(year, month, day) | DATE/TIME | Returns a date string built from year, month, and day numbers. |
| DAY(date$)              | DATE/TIME   | Returns the day of the month (1-31) from a date string. |
| DAYSINMONTH(month, year) | DATE/TIME | Returns the number of days in the given month and year. (year, month) is also accepted. |
| DAYSINYEAR(year)        | DATE/TIME   | Returns 365 or 366 depending on whether the year is a leap year. |
| DEGREES(radians)        | MATH        | Converts an angle from radians to degrees. |
| DISKSPACE(path$)        | FILE        | Returns the number of free bytes on the disk containing the specified path. |
| ENDSWITH(string$, suffix$) | STRING   | Returns true (-1) if string$ ends with suffix$, otherwise false (0). |
| ENVIRON$(var_name$)     | INFO        | Returns the value of a system environment variable. |
| EOF(file_num)           | FILE        | Returns true (-1) if the end of the specified file handle has been reached, otherwise false (0). |
| EXP(number)             | MATH        | Returns e (the base of natural logarithms) raised to the power of number. |
| EXTRACT$(string$, position, [delimiter$]) | STRING | Returns the field at position (1-based) when string$ is split on delimiter$ (default comma). |
| FILE_EXISTS(path$)      | FILE        | Returns true (-1) if the specified file or directory path exists, otherwise false (0). |
| FILEATTR(path$)         | FILE        | Returns a number representing the file's attributes (e.g., read-only, directory). |
| FILESIZE(path$)         | FILE        | Returns the size of the specified file in bytes. Returns -1 if the file doesn't exist. |
| FILETIME(path$)         | FILE        | Returns the last modification timestamp of the file as a string (e.g., "YYYY-MM-DD HH:MI:SS"). |
| FILTER(array, criteria) | ARRAY/HOF   | Returns a new array of elements matching criteria. The criteria can be a substring (case-sensitive match against str(item)) OR a bare function name (UDF or built-in) called with each item. Optional third arg = 0 inverts (returns non-matches). |
| FIND(array, value)      | ARRAY       | Returns the zero-based index of the first occurrence of value in an array. Returns -1 if not found. |
| FIX(number)             | MATH        | Truncates the decimal part of a number. |
| FLOOR(number)           | MATH        | Rounds a number down to the nearest integer. |
| FORMAT$(value, mask$)   | STRING      | Formats a value according to a numeric mask (e.g. `"#,##0.00"`, `"$#,##0"`, `"0.00%"`). |
| FORMATDATE$(date$, output_mask$, [input_mask$]) | DATE/TIME | Formats a date string according to a specified mask (e.g. "YYYY-MM-DD"). Optional input_mask$ tells DbBasic how to parse the input. |
| FREEFILE()              | FILE        | Returns the next available integer for use as a file handle. |
| HASH_COUNT(hash)        | HASH        | Returns the number of key-value pairs in a hash. |
| HASH_DELETE(hash, key$) | HASH        | Deletes a key-value pair from a hash. Use it in an expression (`r = HASH_DELETE(h, k$)`); it returns -1 if the key was deleted, 0 if it was not present. |
| HASH_EXISTS(hash, key$) | HASH        | Returns true (-1) if the key$ exists in the hash, otherwise false (0). |
| HASH_JOIN(hash1, hash2, ...) | HASH   | Merges two or more hashes into a new hash. Keys from later hashes overwrite earlier ones. |
| HASH_KEYS(hash)         | HASH        | Returns an ARRAY containing all the keys from a hash. |
| HASH_RENAME(hash, old_key$, new_key$) | HASH | Renames a key in a hash. |
| HASH_VALUES(hash)       | HASH        | Returns an ARRAY containing all the values from a hash. |
| HEX$(number)            | STRING      | Returns the hexadecimal representation of a number as a string. |
| HTMLDECODE$(string$)    | STRING      | Decodes HTML entities back to characters. |
| HTMLENCODE$(string$)    | STRING      | Encodes a string for safe inclusion in HTML. |
| INKEY$ / INKEY$(seconds) | SCREEN     | Returns the key pressed ("" if none). INKEY$(0) waits for a key. Special keys come back as names such as UP or F1. |
| INSTR([start_pos,] haystack$, needle$) | STRING | Finds the starting position of needle$ within haystack$. Returns 0 if not found. |
| INSTRREV(haystack$, needle$, [start]) | STRING | Like INSTR but searches from the end. start limits where the search ends. |
| INT(number)             | MATH        | Returns the integer portion of a number by rounding down (same as FLOOR). |
| IS_ARRAY(variable)      | ARRAY       | Returns true (-1) if the variable is an ARRAY, otherwise false (0). |
| IS_HASH(variable)       | HASH        | Returns true (-1) if the variable is a HASH, otherwise false (0). |
| ISALNUM(string$)        | STRING      | Returns true (-1) if all characters in the string are alphanumeric, otherwise false (0). |
| ISALPHA(string$)        | STRING      | Returns true (-1) if all characters in the string are alphabetic, otherwise false (0). |
| ISDATE(string$)         | DATE/TIME   | Returns true (-1) if the string parses as a date, otherwise false (0). |
| ISDIGIT(string$)        | STRING      | Returns true (-1) if all characters in the string are digits, otherwise false (0). |
| ISLEAP(year)            | DATE/TIME   | Returns true (-1) if the year is a leap year, otherwise false (0). |
| ISNUMERIC(string$)      | STRING      | Returns true (-1) if the string parses as a number, otherwise false (0). |
| JSON_SERIALIZE$(variable, [indent], [options...]) | HASH/ARRAY | Converts a DbBasic HASH or ARRAY into a JSON formatted string. |
| LASTKEY$                | SCREEN      | The key that ended the last READ, MENU or BROWSE. |
| LCASE$(string$)         | STRING      | Converts a string to all lowercase characters. |
| LEFT$(string$, length)  | STRING      | Returns the first length characters from the left of the string. |
| LEN(value)              | STRING      | Returns the number of characters in the string representation of a value. |
| LOG(number)             | MATH        | Returns the natural logarithm of a number. |
| LTRIM$(string$)         | STRING      | Removes whitespace from the beginning (left side) of a string. |
| MAP(array, fn)          | ARRAY/HOF   | Returns a new array with each element passed through fn (a UDF or built-in name). |
| MAX(num1, num2, ...)    | MATH        | Returns the largest number from a list of arguments. |
| MENU(row, col, item$, ...) | SCREEN   | Shows a light-bar menu and returns the chosen item number (0 for Esc). |
| MENUBAR$([row,] "Title:item|...", ...) | SCREEN | Shows a menu bar with pull-down menus and returns "Title.Item" ("" for Esc). |
| MID$(string$, start_pos, [length]) | STRING | Returns a substring of a specified length starting from start_pos. |
| MIN(num1, num2, ...)    | MATH        | Returns the smallest number from a list of arguments. |
| MOD(number1, number2)   | MATH        | Returns the remainder of number1 divided by number2. |
| MONTH(date$)            | DATE/TIME   | Returns the month (1-12) from a date string. |
| MONTHCAL$(year, month)  | DATE/TIME   | Returns a calendar of the given month as a multi-line string. |
| MONTHNAME$(month_num)   | DATE/TIME   | Returns the English name of the given month (1-12). |
| MOUSECOL                | SCREEN      | The column of the last mouse click or wheel turn. |
| MOUSEROW                | SCREEN      | The row of the last mouse click or wheel turn. |
| NOW()                   | DATE/TIME   | Returns the current date and time as "YYYY-MM-DD HH:MI:SS". |
| NVL(value, default, ...) | UTILITY    | Returns the first argument that is not empty (`""` or 0). |
| OCT$(number)            | STRING      | Returns the octal representation of a number as a string. |
| ORDINAL$(number)        | STRING      | Returns the English ordinal words for a number (e.g. 1 → "first", 21 → "twenty-first", 100 → "one hundredth"). |
| PADLEFT$(text$, length, pad_char$) | STRING | Pads a string on the left to a total length using pad_char$. |
| PADRIGHT$(text$, length, pad_char$) | STRING | Pads a string on the right to a total length using pad_char$. |
| PARSEJSON(string$)      | HASH/ARRAY  | Parses a JSON string into a HASH or ARRAY. |
| PATHNAME$(path$)        | FILE        | Returns the directory portion of a path. |
| POWER(base, exponent)   | MATH        | Returns the value of base raised to the power of exponent. |
| PROPER$(string$)        | STRING      | Converts a string to title case (e.g., "hello world" becomes "Hello World"). |
| RADIANS(degrees)        | MATH        | Converts an angle from degrees to radians. |
| REDUCE(array, fn, [initial]) | ARRAY/HOF | Folds an array into a single value using fn(acc, item). If initial is omitted, the first element is used as the initial accumulator. |
| REPEAT$(string$, count) | STRING      | Returns a string consisting of string$ repeated count times. |
| REPLACE$(source$, old$, new$, [count], [ignore_case]) | STRING | Replaces occurrences of old$ with new$ in the source$ string. |
| REVERSE$(string$)       | STRING      | Reverses the order of characters in a string. |
| RIGHT$(string$, length) | STRING      | Returns the last length characters from the right of the string. |
| RND([max_val])          | MATH        | Returns a random number. If max_val is provided, returns an integer between 1 and max_val. Otherwise, returns a float between 0 and 1. |
| ROUND(number, [decimals]) | MATH      | Rounds a number to a specified number of decimals. |
| RTRIM$(string$)         | STRING      | Removes whitespace from the end (right side) of a string. |
| SAVESCREEN([top, left, bottom, right]) | SCREEN | Copies the screen or an area (with colours) into a string for `RESTSCREEN`. |
| SECOND(time$)           | DATE/TIME   | Returns the seconds component (0-59) from a time/datetime string. |
| MINUTE(time$)           | DATE/TIME   | Returns the minutes component (0-59) from a time/datetime string. |
| HOUR(time$)             | DATE/TIME   | Returns the hours component (0-23) from a time/datetime string. |
| SGN(number)             | MATH        | Returns the sign of a number (-1 for negative, 0 for zero, 1 for positive). |
| SIN(number)             | MATH        | Returns the sine of an angle given in radians. |
| SOUNDEX$(string$)       | STRING      | Returns the Soundex phonetic code of a string. |
| SPACE$(count)           | STRING      | Returns a string consisting of count spaces. |
| SPLIT(string$, delimiter$, [limit]) | ARRAY | Splits a string by a delimiter$ and returns an ARRAY of substrings. |
| SQR(number)             | MATH        | Returns the square root of a number. |
| STARTSWITH(string$, prefix$) | STRING | Returns true (-1) if string$ starts with prefix$, otherwise false (0). |
| STR$(number)            | STRING      | Converts a number to a string as `PRINT` shows it, with a leading space for zero and positive numbers. |
| STRIPHTML$(string$)     | STRING      | Removes HTML tags from a string. |
| TAN(number)             | MATH        | Returns the tangent of an angle given in radians. |
| TIME$()                 | DATE/TIME   | Returns the current system time as an "HH:MI:SS" string. |
| TRIM$(string$)          | STRING      | Removes whitespace from both the beginning and end of a string. |
| TYPENAME$(value)        | UTILITY     | Returns the name of the value's type: "FLOAT", "STRING", "ARRAY" or "HASH". |
| UBOUND(array)           | ARRAY       | Returns the upper bound (the highest index) of an array. Returns -1 for an empty array. |
| UCASE$(string$)         | STRING      | Converts a string to all uppercase characters. |
| URL_FILENAME$(url$)     | STRING      | Returns the filename portion of a URL path. |
| URL_HOSTNAME$(url$)     | STRING      | Returns the hostname component of a URL. |
| URL_PATH$(url$)         | STRING      | Returns the directory portion of a URL path. |
| URL_SCHEME$(url$)       | STRING      | Returns the scheme (e.g., "http", "https") of a URL. |
| URLDECODE$(string$)     | STRING      | URL-decodes a percent-encoded string. |
| URLENCODE$(string$)     | STRING      | Percent-encodes a string for safe use in a URL. |
| VAL(string$)            | STRING/MATH | Returns the number at the start of string$ (`VAL("12abc")` is 12), or 0. |
| WEEKDAY(date$)          | DATE/TIME   | Returns the day of the week as a number (1 for Sunday, 7 for Saturday). |
| WEEKDAYNAME$(weekday_num) | DATE/TIME | Returns the English name of the given weekday (1 = Sunday ... 7 = Saturday, matching WEEKDAY). |
| YEAR(date$)             | DATE/TIME   | Returns the year from a date string. |
| YEARCAL$(year)          | DATE/TIME   | Returns a calendar of the given year as a multi-line string. |

---

**Note:** All functions return a value and can be used in expressions, assignments, or as arguments to other functions/statements.

### Function References as First-Class Arguments

`FILTER`, `MAP`, `REDUCE`, and `SORT WITH` accept a bare function name (without parentheses) as a first-class argument. The name may be a user-defined function or any of the built-ins above. Examples:

```basic
upper_names = MAP(names, UCASE$)
positives   = FILTER(values, ISNUMERIC)
total       = REDUCE(amounts, MAX)
SORT items WITH UCASE$ ASC
```

### String Interpolation in Backtick Strings

Backtick-delimited string literals support `${expr}` interpolation. Expressions may include arithmetic, built-in calls, UDF calls, and hash/array access:

```basic
PRINT `Hello, ${name$}!`
PRINT `Total: ${FORMAT$(amount, "$#,##0.00")}`
PRINT `Row ${i}: ${row("city$")} (${CARDINAL$(row("count"))})`
```

`$$` produces a literal `$`. Lone `{` and `}` are literal, so JSON, regex, and code snippets pass through intact. Regular double-quoted strings are unaffected.
