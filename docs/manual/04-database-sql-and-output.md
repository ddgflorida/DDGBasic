# Chapter 4: Database, SQL & Output

DbBasic embeds a relational database in the language. Every program starts with an open in-memory **SQLite** connection. SQL statements can be written directly in the source, without quoting or a wrapper call. This chapter covers:

- the `DATABASE` statement, which selects the engine (SQLite or DuckDB) and the database file
- how the lexer recognises embedded SQL and how it runs
- bind variables, transactions and the SQL status variables
- scalar subqueries, `IF EXISTS`, `IN (SELECT ...)` and `FOR row IN (SELECT ...)`
- dynamic SQL with `EXECUTE`
- schema inspection with `SHOW` and `DESCRIBE`
- SQL error handling
- the `SET` statement and the result-set output pipeline (`SET OUTPUT ... FORMAT ...`)
- console and file output with `PRINT`, `PRINT USING`, `WRITE` and `ECHO`

Related chapters:

- Chapter 1 (Language Fundamentals): variables, hashes and backtick string interpolation (`${(SELECT ...;)}`).
- Chapter 2 (Control Flow & Procedures): `IF`, `FOR`, `EXIT FOR`, `ON ERROR GOTO`.
- Chapter 3 (Built-in Functions): `FORMAT$` and the extra SQL functions that are registered with SQLite.
- Chapter 5 (Data Loading, Conversion & Analysis): `LOAD`, `ANALYZE` and `UPGRADE`, which fill tables that are then queried with the statements here.
- Chapter 6 (Files, System, Network & UI): `OPEN`/`CLOSE` file handles and `EMAIL`.

All examples in this chapter were run with the interpreter in `src/dbbasic.py`. The output shown is the actual output.

---

## 4.1 The database connection

### 4.1.1 Default connection

When the interpreter starts, it sets `db_engine = 'sqlite'` and calls `_init_db()` with no arguments. This opens an **in-memory SQLite database** (`:memory:`). You can therefore use SQL without any setup:

```basic
CREATE TABLE t (id INTEGER);
INSERT INTO t VALUES (1);
SELECT * FROM t;
```

Connection details that follow from `_init_db()`:

| Engine | How it is opened | Notes |
|---|---|---|
| SQLite | `sqlite3.connect(filename, isolation_level=None)` | Autocommit mode. Each statement commits on its own unless you issue `BEGIN`. DbBasic's extra string functions are registered on this connection (see 4.11). |
| DuckDB | `duckdb.connect(database=filename, read_only=False)` | Autocommit by default. DbBasic's extra SQLite functions are **not** registered. Use DuckDB's built-in functions instead. |

Only one connection is active at a time. Opening a new database closes the current one first.

### 4.1.2 DATABASE OPEN

```
DATABASE OPEN filename_expression
```

Closes the current connection and opens `filename_expression` with the **current engine**. The argument is any expression, so it can be a string literal, a variable or a concatenation. If the file does not exist, it is created. Use `":memory:"` for a new, empty in-memory database.

```basic
DATABASE OPEN "test.db"
CREATE TABLE IF NOT EXISTS k (v TEXT);
INSERT INTO k VALUES ('persisted');
DATABASE CLOSE
SELECT name FROM sqlite_master;
DATABASE OPEN "test.db"
SELECT * FROM k;
```

Output:

```
(0 rows returned)
+-----------+
|     v     |
+-----------+
| persisted |
+-----------+
(1 rows returned)
```

### 4.1.3 DATABASE CLOSE

```
DATABASE CLOSE
```

Closes the current connection and **immediately opens a new in-memory database** with the current engine. There is never a state with no connection, so SQL that follows a `DATABASE CLOSE` runs against an empty `:memory:` database. That is why the first `SELECT` above returned 0 rows instead of failing.

### 4.1.4 DATABASE ENGINE

```
DATABASE ENGINE SQLITE
DATABASE ENGINE DUCKDB
```

Selects the backend. The engine name is not case-sensitive. Any other name raises `Unsupported engine. Use SQLITE or DUCKDB.`

Switching engines **closes the current connection and opens a new in-memory database** with the new engine. Tables in the old connection are not carried over, and this happens even when the engine named is the one already in use. If you want a file-based database on the new engine, issue `DATABASE OPEN` *after* `DATABASE ENGINE`:

```basic
DATABASE ENGINE DUCKDB
DATABASE OPEN "test.duckdb"
CREATE TABLE IF NOT EXISTS d (v VARCHAR);
INSERT INTO d VALUES ('duck');
SELECT * FROM d;
DATABASE ENGINE SQLITE
SELECT COUNT(*) AS tables FROM sqlite_master;
```

Output:

```
+------+
|  v   |
+------+
| duck |
+------+
(1 rows returned)
+--------+
| tables |
+--------+
| 0      |
+--------+
(1 rows returned)
```

The engine setting changes the behaviour of several statements: `EXECUTE`, `SHOW INDEXES`, `SHOW CREATE TABLE`, `DESCRIBE` and `FORMAT SQL` (its default `vendor`). Section 4.12 summarises the differences.

---

## 4.2 Embedded SQL statements

### 4.2.1 Which lines are treated as SQL

The lexer switches into SQL mode when **the first token on a source line** is one of these keywords (any case):

```
SELECT  INSERT  UPDATE  DELETE  CREATE  DROP  ALTER
WITH    BEGIN   COMMIT  ROLLBACK  ATTACH  COPY
SUMMARIZE  PRAGMA  END TRANSACTION
```

When the lexer sees one of these keywords at the start of a line, it searches forward in the source for the next semicolon. Everything from the keyword up to and including that semicolon becomes a single `SQL_STRING` token. The interpreter passes that text to the database unchanged, apart from the rewrites described below.

The SQL text can use any SQL syntax, including operators that are not BASIC characters, such as `||` (string concatenation), `~`, `|`, `%` and `<<`:

```basic
select 'Hello World' || ' how are you';
```

```
+---------------------------------+
| 'Hello World' || ' how are you' |
+---------------------------------+
| Hello World how are you         |
+---------------------------------+
(1 rows returned)
```

Consequences:

- **The semicolon is required.** A SQL statement without a terminating `;` is not recognised as SQL. You get `Unknown statement: SELECT`, but only if there is no semicolon anywhere later in the file.
- **SQL can span multiple lines.** The statement ends at the first `;`, however many lines later that is:

  ```basic
  INSERT INTO emp VALUES (1, 'Alice', 'Sales', 52000),
                         (2, 'Bob', 'IT', 61000),
                         (3, 'Carol', 'IT', NULL);
  ```

- **A missing semicolon swallows the following lines.** The search for `;` ignores line boundaries and BASIC syntax, so the next semicolon anywhere in the source ends the statement:

  ```basic
  SELECT 1 AS a
  PRINT "x"; "y"
  ```

  This sends `SELECT 1 AS a\nPRINT "x";` to SQLite, which fails with `near "PRINT": syntax error`.
- **Indentation is allowed.** Leading spaces and tabs do not count as tokens, so an indented SQL line inside `IF`/`FOR`/`WHILE` blocks still starts in SQL mode.
- **Only the start of a line counts.** SQL is not recognised after `THEN`, after a `:` statement separator, or after a label:

  ```basic
  IF x = 1 THEN SELECT 'inline' AS v;     ' Runtime Error: Unknown statement: SELECT
  start: SELECT 'labelled' AS v;          ' Runtime Error: Unknown statement: SELECT
  ```

  Use a block `IF ... END IF` and put the SQL on a line of its own:

  ```basic
  IF x = 1 THEN
     SELECT 'block' AS v;
  END IF
  ```

- **One SQL statement per line.** After the first `;`, the rest of the line is parsed as BASIC. `select 1 as a; select 2 as b;` runs the first query, then fails with `Unknown statement: SELECT`. To run several statements from one line or one string, use `EXECUTE` (4.6).
- **The keywords are effectively reserved.** A line that starts with, for example, `update` or `copy` is treated as SQL when a semicolon follows it anywhere later in the file.

### 4.2.2 Keyword joining and SQL text

Before tokenising, the lexer joins certain multi-word keywords into single tokens:

| Code (any case, any whitespace) | Becomes |
|---|---|
| `END IF` | `ENDIF` |
| `LINE INPUT` | `LINEINPUT` |
| `END LOOP` | `ENDLOOP` |
| `FOR EACH` | `FOREACH` |
| `END TRANSACTION` | `ENDTRANSACTION` |
| `READ FILE` | `READFILE` |
| `TO FILE` / `INTO FILE` | `TOFILE` / `INTOFILE` |
| `ANALYZE CSV` / `FIXED` / `JSONL` / `JSON` / `XML` / `TEXT` | `ANALYZECSV` etc. |
| `ON ERROR GOTO` | `ONERRORGOTO` |
| `END FORM` / `OPEN FORM` / `END FUNCTION` | `ENDFORM` / `OPENFORM` / `ENDFUNCTION` |
| `WITH DETAILS` / `WITH FULLPATH` / `WITH FOLDERSONLY` / `WITH FILESONLY` | joined |
| `LIST FIELDS` | `LISTFIELDS` |

These rewrites apply only to code. Text inside `"..."`, `'...'` and backtick strings, and inside `REM` and `--` comments, is left as written, so SQL string literals reach the engine unchanged:

```basic
SELECT 'for each item' AS a, 'end if' AS b;
```

```
+---------------+--------+
|       a       |   b    |
+---------------+--------+
| for each item | end if |
+---------------+--------+
(1 rows returned)
```

A keyword pair written as SQL code (not inside quotes) is joined while the line is tokenised, then split back apart in the SQL text sent to the engine. So `END TRANSACTION;` and `CREATE TRIGGER ... FOR EACH ROW` reach the database as written, apart from letter case.

### 4.2.3 Semicolons and comments inside SQL

A line-level SQL statement ends at the first `;` that is **outside** all of the following:

- single-quoted string literals (`'a;b'`, including `''` escapes such as `'it''s'`)
- double-quoted identifiers (`"semi;col"`)
- `--` comments
- `/* */` comments

The statement can span several lines.

```basic
INSERT INTO t VALUES (1, 'a;b');
INSERT INTO t VALUES (2, 'it''s; fine');
INSERT INTO t VALUES (3, 'x') -- trailing; comment
;
SELECT id, note FROM t /* block; comment */ ORDER BY id;
```

```
+----+------------+
| id |    note    |
+----+------------+
| 1  | a;b        |
| 2  | it's; fine |
| 3  | x          |
+----+------------+
(3 rows returned)
```

A quote that is never closed stops the program before it runs, with `Unexpected character '''`. A statement with no terminating `;` is not treated as SQL and fails with `Unknown statement`. `EXECUTE` splits multi-statement strings by the same rules (4.6).

Comments are passed through to the engine, which ignores them.

A `CREATE [TEMP] TRIGGER` statement ends at the first `;` after the `END` that closes its `BEGIN`, so the `;` after each statement in the body doesn't end it. `CASE ... END` inside the body nests correctly. `EXECUTE` splits trigger statements the same way.

```basic
CREATE TRIGGER trg AFTER INSERT ON t FOR EACH ROW
BEGIN
  INSERT INTO log VALUES ('added ' || NEW.a);
  INSERT INTO log VALUES (CASE WHEN NEW.a > 1 THEN 'big' ELSE 'small' END);
END;
```

### 4.2.4 How the statement runs

The parser receives the `SQL_STRING` token and records its text in `last_sql_statement` (`FORMAT SQL` uses it to infer a table name). It then branches on the first word:

- If the text starts with `SELECT`, `WITH`, `SUMMARIZE` or `PRAGMA`, it is treated as a **query**. If `SET OUTPUT OFF` is active, the statement is **skipped without being executed**. Otherwise the statement runs, all rows are fetched, and the rows and column names go to the output pipeline (`_handle_output`, 4.10).
- Any other text (`INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `BEGIN`, `COMMIT`, `ROLLBACK`, `ATTACH`, `COPY`) runs as a **command**. No result is displayed, even when the statement could return rows (for example `INSERT ... RETURNING`).

A `PRAGMA` that sets a value returns no rows, so it prints `(0 rows returned)` in the default format.

### 4.2.5 Default display of query results

The default output format is `TEXT`. It prints an ASCII-bordered table with:

- centred headers
- left-aligned cells
- `NULL` for null values
- a footer line `(n rows returned)`

```basic
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary REAL);
INSERT INTO emp VALUES (1, 'Alice', 'Sales', 52000),
                       (2, 'Bob', 'IT', 61000),
                       (3, 'Carol', 'IT', NULL);
SELECT * FROM emp;
SELECT dept, COUNT(*) AS n FROM emp GROUP BY dept ORDER BY dept;
```

```
+----+-------+-------+---------+
| id | name  | dept  | salary  |
+----+-------+-------+---------+
| 1  | Alice | Sales | 52000.0 |
| 2  | Bob   | IT    | 61000.0 |
| 3  | Carol | IT    | NULL    |
+----+-------+-------+---------+
(3 rows returned)
+-------+---+
| dept  | n |
+-------+---+
| IT    | 2 |
| Sales | 1 |
+-------+---+
(2 rows returned)
```

The footer always says "rows", even for one row. A query that returns nothing prints only `(0 rows returned)`. A cell value that contains newlines is printed on several physical lines inside the table. Section 4.10 covers the other formats and options (box drawing, no header, no footer).

### 4.2.6 Transactions

The SQLite connection runs in autocommit mode (`isolation_level=None`). You control transactions explicitly with `BEGIN`, `COMMIT` and `ROLLBACK`. These are passed straight to the engine, so `BEGIN TRANSACTION;` and the engine's other variants work.

```basic
CREATE TABLE acct (id INTEGER, bal REAL);
INSERT INTO acct VALUES (1, 100);
BEGIN TRANSACTION;
UPDATE acct SET bal = bal - 30 WHERE id = 1;
ROLLBACK;
SELECT bal FROM acct;
BEGIN;
UPDATE acct SET bal = bal - 30 WHERE id = 1;
COMMIT;
SELECT bal FROM acct;
```

```
+-------+
|  bal  |
+-------+
| 100.0 |
+-------+
(1 rows returned)
+------+
| bal  |
+------+
| 70.0 |
+------+
(1 rows returned)
```

`END TRANSACTION;` is a synonym for `COMMIT;` on both engines.

### 4.2.7 SQL status variables

Every call to the internal `_execute_sql` resets these variables. They are visible to the program (for example with `SHOW VARIABLES`):

| Variable | After a successful command (INSERT/UPDATE/DELETE...) | After a query (SELECT...) | After an error |
|---|---|---|---|
| `ERR` | `0` | `0` | `1` |
| `ERRMSG$` | `""` | `""` | the driver's message |
| `SQL_ROWCOUNT` | rows affected (driver `rowcount`; `-1` becomes `0`) | `0` | `0` |
| `SQL_FOUND` | `-1` (true) if rows affected > 0, else `0` | `0` | `0` |
| `SQL_NOTFOUND` | `0` if rows affected > 0, else `-1` (true) | `-1` | `-1` |

```basic
UPDATE emp SET salary = 60000 WHERE dept = 'IT';
PRINT "rows updated:"; SQL_ROWCOUNT, SQL_FOUND, SQL_NOTFOUND
```

```
rows updated: 2	-1	 0
```

`SQL_ROWCOUNT` etc. are **not** set for queries, so you cannot use them to count `SELECT` rows. Use `SELECT COUNT(*)` in a scalar subquery instead. Statements such as `CREATE TABLE` report `SQL_ROWCOUNT = 0`.

---

## 4.3 Bind variables (parameter substitution)

Inside any SQL text that DbBasic runs, a word of the form `:name` is replaced by a `?` placeholder. The value of the BASIC variable `name` is passed as a parameter. This applies to:

- line SQL
- subqueries
- `FOR ... IN (SELECT ...)`
- `EXECUTE`

Values are never pasted into the SQL text, so there is no SQL injection risk and no need to escape quotes.

A bind variable is a `:` followed by a name. The scan (`_find_bind_variables`) skips text inside `'...'` strings, `"..."` identifiers and `--` / `/* */` comments. It also skips a `:` that directly follows another `:` or a name character. So these are **not** bind variables:

- DuckDB casts: `'42'::INTEGER`
- list slices: `arr[a:b]`
- literals: `':memory:'`, `'10:30'`

so the following forms are accepted:

| Form | Example | Meaning |
|---|---|---|
| simple variable | `:id`, `:name$` | the variable's value |
| hash field (dot notation) | `:h.city$`, `:row.ID` | a key in a hash variable (nested dots allowed) |

Variable names are case-insensitive (`:Total` and `:total` are the same variable). Array elements such as `:a(1)` are **not** supported.

```basic
CREATE TABLE t (id INTEGER, name TEXT);
name$ = "Dave" : id = 7
INSERT INTO t VALUES (:id, :name$);
h.city$ = "Miami"
INSERT INTO t VALUES (8, :h.city$);
SELECT * FROM t WHERE id >= :id;
```

```
+----+-------+
| id | name  |
+----+-------+
| 7  | Dave  |
| 8  | Miami |
+----+-------+
(2 rows returned)
```

Behaviour and edge cases:

- **Numbers are bound as floating point.** BASIC numbers are Python floats, so `SELECT :i AS i;` with `i = 1` displays `1.0`. A column with `INTEGER` affinity (SQLite) or type (DuckDB) converts the value on insert, which is why `7` above is stored as an integer.
- **An undefined variable is a hard error.** Bind lookup does not auto-create variables. A missing name raises `Bind variable ':x' not found in internal state.`. This error is raised regardless of `SET SQL_FATAL_ERRORS` (it is not a database error).
- **Colons in literals and casts are left alone:**

  ```basic
  DATABASE ENGINE DUCKDB
  v = 21
  SELECT '42'::INTEGER + 1 AS cast_ok, (:v)::VARCHAR AS v_text, 'a:b' AS lit;
  ```

  ```
  +---------+--------+-----+
  | cast_ok | v_text | lit |
  +---------+--------+-----+
  | 43      | 21.0   | a:b |
  +---------+--------+-----+
  (1 rows returned)
  ```

---

## 4.4 SQL inside expressions

This section is a summary. Chapters 1 and 2 cover the expression and condition grammar.

The lexer also recognises a SQL subquery when a `(` is immediately followed by a SQL keyword. This applies after `=`, `IN` or `EXISTS`, or at any other point where an expression can contain `(`. The text up to the **matching** close parenthesis becomes a `SQL_STRING`. Parenthesis matching skips `'...'` string literals. A trailing `;` inside the parentheses is optional and is ignored by both engines.

### 4.4.1 Scalar subquery

```
variable = (SELECT ...)
```

The query must return exactly one row with exactly one column, otherwise the program stops with `Scalar subquery must return one row/column.`. This includes the zero-row case. A subquery can appear anywhere a value can, including inside a larger expression or a `PRINT` list.

```basic
n = (SELECT COUNT(*) FROM emp)
PRINT "count:"; n
top$ = (SELECT name FROM emp ORDER BY salary DESC LIMIT 1;)
PRINT "top: "; top$
mx = (SELECT MAX(id) * 10 FROM emp) + 5
PRINT "direct:"; (SELECT COUNT(*) FROM emp)
```

```
count: 3
top: Bob
 35
direct: 3
```

A SQL `NULL` result is assigned as an empty value: `""` for a `$` variable, `0` for a numeric one.

### 4.4.2 EXISTS and IN

```basic
IF EXISTS (SELECT 1 FROM emp WHERE dept = 'IT') THEN PRINT "IT exists"
IF "Bob" IN (SELECT name FROM emp) THEN PRINT "Bob found"
```

```
IT exists
Bob found
```

- `EXISTS (SELECT ...)` is true (`-1`) when the query returns at least one row.
- `expr IN (SELECT ...)` collects the **first column** of every row into a set and tests membership with Python equality. Types must match: the number `1` equals SQLite's integer `1`, but the string `"1"` does not.

---

## 4.5 FOR row IN (SELECT ...): iterating a result set

```
FOR var IN (SELECT ...)
    statements
NEXT [var]
```

When the token after `IN` is not `CSV`, `JSONL`, `JSON`, `FILES` or `TEXT`, the loop is a SQL loop. Chapter 2 describes the other loop forms.

How it works (`_parse_for_in_sql_loop`):

1. The query runs once and **all rows are fetched up front**. SQL statements inside the loop body therefore cannot disturb the iteration, and changes they make are not seen by the current loop.
2. Column names are taken from the cursor and **upper-cased**.
3. For each row, `var` is set to a **hash** that contains:
   - each column value under its upper-cased name (`"NAME"`)
   - each column value under its 1-based position as a string key (`"1"`, `"2"`, ...)
4. SQL `NULL` values become `""` (empty string).
5. The built-in variable `RECNO` holds the 1-based row number.
6. If the query returns no rows, the body is skipped.
7. `EXIT FOR` leaves the loop.
8. When the loop ends, `var` is restored to the value it had before the loop, or deleted if it did not exist. `RECNO` is deleted.

Column access uses the normal hash syntax (see [1.11](01-language-fundamentals.md#111-hashes)). The dot form is case-insensitive: `row.name`, `row.NAME` and `row.Name` all work. The parenthesised form matches the key exactly, and column keys are stored upper-cased, so `row("PAY")` and `row("1")` work but `row("pay")` returns the default value (`0`) unless `SET HASH_KEYS IGNORE_CASE` is on. Use an `AS` alias to give computed columns a usable name.

```basic
CREATE TABLE emp (id INTEGER, name TEXT, dept TEXT, salary REAL);
INSERT INTO emp VALUES (1, 'Alice', 'Sales', 52000), (2, 'Bob', 'IT', 61000), (3, 'Carol', 'IT', NULL);
FOR r IN (SELECT id, name, salary AS pay FROM emp ORDER BY id)
  PRINT RECNO; r.name; r("PAY"); r("1"); r.Name
NEXT r
FOR r IN (SELECT * FROM emp WHERE id > 99)
  PRINT "never"
NEXT
PRINT "end"
```

```
 1Alice 52000 1Alice
 2Bob 61000 2Bob
 3Carol 3Carol
end
```

Carol's `NULL` salary shows as an empty string.

Running SQL inside the loop body is allowed. Bind variables can refer to the loop hash or to derived variables:

```basic
DATABASE ENGINE DUCKDB
CREATE TABLE d (k VARCHAR, n INTEGER);
INSERT INTO d VALUES ('a', 1), ('b', 2), ('c', 3);
CREATE TABLE log (msg VARCHAR);
FOR row IN (SELECT k, n * 1.5 AS x FROM d ORDER BY k)
  m$ = row.k + "!"
  INSERT INTO log VALUES (:m$);
  IF row.k = "b" THEN EXIT FOR
  PRINT RECNO; " "; row.k; row.x
NEXT
SELECT * FROM log;
```

```
 1 a1.5
+-----+
| msg |
+-----+
| a!  |
| b!  |
+-----+
(2 rows returned)
```

DuckDB returns `DECIMAL` columns as Python `Decimal` objects. `PRINT` does not treat them as numbers, so there is no leading sign space (`1.5` rather than ` 1.5`), but arithmetic on them works. `DOUBLE`/`INTEGER` columns print like normal numbers.

---

## 4.6 EXECUTE: dynamic SQL

```
EXECUTE string_expression
```

`EXECUTE` evaluates its argument and runs the result as **SQL**. The argument must be a string, otherwise the program stops with `Argument for EXECUTE must be a string containing SQL statement(s).`. Bind variables (`:name`) are resolved as usual. `EXECUTE` resets `ERR`, `ERRMSG$`, `SQL_ROWCOUNT`, `SQL_FOUND` and `SQL_NOTFOUND`.

**SQLite.** The string is split into separate statements by `_split_sql_statements`. That splitter, unlike the line scanner:

- ignores `;` inside `'...'` literals, `-- ...` comments and `/* ... */` comments
- removes the comments themselves

Each statement then runs in turn:

- A statement starting with `SELECT`, `WITH` or `PRAGMA` is run as a query. Its rows go to the output pipeline, **but only when there is at least one row**. An empty result prints nothing, not even `(0 rows returned)`. `SUMMARIZE` is not in this list.
- Any other statement runs as a command.

**DuckDB.** The whole string is passed in a single `execute` call. DuckDB runs every statement in it, but **no results are displayed**, even for a trailing `SELECT`.

```basic
tbl$ = "items"
EXECUTE "CREATE TABLE " + tbl$ + " (id INTEGER, label TEXT)"
EXECUTE "INSERT INTO items VALUES (1, 'one'); INSERT INTO items VALUES (2, 'two;2'); -- comment" + CHR$(10) + "SELECT * FROM items"
lbl$ = "three"
EXECUTE "INSERT INTO items VALUES (3, :lbl$)"
PRINT "rowcount:"; SQL_ROWCOUNT
EXECUTE "SELECT * FROM items WHERE id = 99"
PRINT "nothing printed for empty result"
SET SQL_FATAL_ERRORS OFF
EXECUTE "SELECT * FROM missing"
PRINT "ERR="; ERR; " "; ERRMSG$
```

```
+----+-------+
| id | label |
+----+-------+
| 1  | one   |
| 2  | two;2 |
+----+-------+
(2 rows returned)
rowcount: 1
nothing printed for empty result

--- FAILED SQL ---
SQL    : SELECT * FROM missing
PARAMS : []
------------------

ERR= 1 no such table: missing
```

`EXECUTE` is also the way to:

- run more than one SQL statement from a single line
- build table or column names at run time (bind variables can only supply *values*)
- send SQL text that contains a `;` inside a literal

To run dynamic **BASIC** code, use `EVAL` (Chapter 2). The built-in `HELP EXECUTE` text describes `EXECUTE` as running code. That description does not match the implementation (see 4.14).

---

## 4.7 Schema inspection: SHOW and DESCRIBE

`SHOW` prints directly to the console with `print`. It ignores `SET OUTPUT`. `DESCRIBE` sends its result through the output pipeline, so it respects `SET OUTPUT`. A trailing `;` is accepted after each form.

### 4.7.1 SHOW TABLES

```
SHOW TABLES [INTO array_variable]
```

Lists user tables, one name per line. If there are none, it prints `No tables found.`.

- SQLite: `sqlite_master` rows with `type='table'`, excluding names that start with `sqlite_`, ordered by name.
- DuckDB: the result of `SHOW TABLES`.

With `INTO`, nothing is printed. The names are stored in the array variable instead (an empty array when there are no tables).

### 4.7.2 SHOW INDEXES

```
SHOW INDEXES [ON table_name]
```

**SQLite only.** For each table, this prints:

- the `CREATE INDEX` statement of every explicit index
- a comment plus a synthetic `CREATE UNIQUE INDEX` for every automatic index created by a `UNIQUE` constraint
- an `ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY (...)` line for every primary-key index

Every printed line ends with `;`. If nothing is found, it prints `No indexes found.` or `No indexes found on table X.`.

**DuckDB:** this branch is not implemented. It always prints `No indexes found.`.

The built-in help shows `SHOW INDEXES FROM "tablename"`, but the parser accepts only `ON`.

### 4.7.3 SHOW CREATE TABLE

```
SHOW CREATE TABLE [table_name]
```

Prints the stored `CREATE TABLE` statement followed by `;` and a blank line. With no name, it prints the statement for every table. If a table is not found, it prints `-- Table 'X' not found or has no CREATE statement.`.

The table name can be:

- a quoted string
- a variable that holds a non-empty string
- a bare identifier that is not the name of an existing variable

Sources:

- SQLite: `sqlite_master.sql`
- DuckDB: `duckdb_tables().sql`

DuckDB regenerates the statement, so quoting and spacing can differ from what you typed, e.g. `CREATE TABLE emp(id INTEGER PRIMARY KEY, "name" VARCHAR, salary DOUBLE);`.

### 4.7.4 SHOW VARIABLES

```
SHOW VARIABLES
```

Prints `--- Current Variables ---`, then one line per variable in the form `name (python_type): value`. Values longer than 50 characters are truncated to 47 characters followed by `...`. This includes the SQL status variables once any SQL has run:

```
--- Current Variables ---
ERR (float): 0.0
ERRMSG$ (str): 
SQL_ROWCOUNT (float): 0.0
SQL_FOUND (float): 0.0
SQL_NOTFOUND (float): -1.0
x$ (str): 
```

Any other word after `SHOW` raises `Expected TABLES, INDEXES, or CREATE TABLE after SHOW`.

### 4.7.5 DESCRIBE

```
DESCRIBE [TABLE] table_name
```

Shows the column structure of a table. The table name follows the same rules as `SHOW CREATE TABLE`.

- SQLite runs `PRAGMA table_info(name)`, which returns the columns `cid, name, type, notnull, dflt_value, pk`.
- DuckDB runs `DESCRIBE name`, which returns the columns `column_name, column_type, null, key, default, extra`.

If the table does not exist, `Table 'X' not found.` is written to stderr.

```basic
CREATE TABLE emp (id INTEGER PRIMARY KEY, email TEXT UNIQUE, dept TEXT);
CREATE INDEX idx_dept ON emp(dept);
CREATE TABLE dept (code TEXT, name TEXT);
SHOW TABLES
SHOW TABLES INTO t
PRINT t
SHOW INDEXES ON emp
SHOW INDEXES ON dept
SHOW CREATE TABLE emp
tn$ = "dept"
DESCRIBE TABLE tn$
```

```
dept
emp
[dept, emp]
CREATE INDEX idx_dept ON emp(dept);
-- UNIQUE constraint implemented by index: sqlite_autoindex_emp_1;
CREATE UNIQUE INDEX sqlite_autoindex_emp_1 ON emp (email);
No indexes found on table dept.
CREATE TABLE emp (id INTEGER PRIMARY KEY, email TEXT UNIQUE, dept TEXT);

+-----+------+------+---------+------------+----+
| cid | name | type | notnull | dflt_value | pk |
+-----+------+------+---------+------------+----+
| 0   | code | TEXT | 0       | NULL       | 0  |
| 1   | name | TEXT | 0       | NULL       | 0  |
+-----+------+------+---------+------------+----+
(2 rows returned)
```

In SQLite, `INTEGER PRIMARY KEY` is an alias for the rowid and has no separate index, so no `ALTER TABLE ... PRIMARY KEY` line appears for `emp`.

The same schema in DuckDB:

```
+-------------+-------------+------+------+---------+-------+
| column_name | column_type | null | key  | default | extra |
+-------------+-------------+------+------+---------+-------+
| id          | INTEGER     | NO   | PRI  | NULL    | NULL  |
| name        | VARCHAR     | YES  | NULL | NULL    | NULL  |
| salary      | DOUBLE      | YES  | NULL | NULL    | NULL  |
+-------------+-------------+------+------+---------+-------+
(3 rows returned)
```

DuckDB's own `SUMMARIZE table;` is recognised as a query and displays per-column statistics (`min`, `max`, `approx_unique`, `avg`, `std`, `q25`, `q50`, `q75`, `count`, `null_percentage`).

---

## 4.8 SQL error handling

When the database driver raises an error (`sqlite3.Error` or `duckdb.Error`), `_execute_sql` does the following:

1. It writes a diagnostic block to **stderr**:

   ```
   --- FAILED SQL ---
   SQL    : <the SQL actually sent, with ? placeholders>
   PARAMS : <list of bound values>
   ------------------
   ```

2. It sets `ERR = 1` and `ERRMSG$` to the driver's message.
3. If `SQL_FATAL_ERRORS` is `ON` (**the default**), it raises a runtime error `Fatal DB Error: <message>`. Otherwise it returns no result and execution continues with the next statement.

A fatal SQL error is an ordinary runtime error, so `ON ERROR GOTO` can trap it (Chapter 2):

```basic
ON ERROR GOTO handler
SELECT * FROM nope;
PRINT "not reached"
END
handler:
PRINT "Trapped: "; ERRMSG$
END
```

```
--- FAILED SQL ---
SQL    : SELECT * FROM nope;
PARAMS : []
------------------

Trapped: Fatal DB Error: no such table: nope at line 2, col 18.
  Context: 'SELECT * FROM nope;' -> ...
```

With `SET SQL_FATAL_ERRORS OFF`, test `ERR` after each statement:

```basic
SET SQL_FATAL_ERRORS OFF
SELECT * FROM nosuch;
IF ERR THEN PRINT "Query failed: "; ERRMSG$
```

The following errors are **not** governed by `SQL_FATAL_ERRORS`. They always stop the program unless trapped:

- unknown bind variables
- scalar subqueries that do not return exactly one value
- output-pipeline errors (for example `FORMAT EXCEL` on the console)

`EXECUTE` and `DESCRIBE` also catch any other Python exception: they set `ERR`/`ERRMSG$` and raise only when `SQL_FATAL_ERRORS` is `ON`.

---

## 4.9 The SET statement

`SET` takes one of the option words below. The option words are recognised as identifiers, so they are not case-sensitive.

| Option | Syntax |
|---|---|
| `OUTPUT` | `SET OUTPUT [CONSOLE \| FILE expr \| OFF] [FORMAT fmt [sql_mode] [OPTIONS "k=v, ..."]]` |
| `SQL_FATAL_ERRORS` | `SET SQL_FATAL_ERRORS ON \| OFF` |
| `HASH_KEYS` | `SET HASH_KEYS PRESERVE_CASE \| IGNORE_CASE` |
| `NULL_HANDLING` | `SET NULL_HANDLING [FOR expr] TO NULL \| CONVERT_EMPTY_TO_NULL \| PRESERVE_EMPTY_STRINGS \| EMPTY` |
| `EMAIL` | `SET EMAIL keyword value [keyword value ...]` |

These are the only options. Any other word after `SET` is an error: `SET x = 5` gives `Unknown SET option 'x'. Expected OUTPUT, EMAIL, NULL_HANDLING, SQL_FATAL_ERRORS or HASH_KEYS.` To change the database engine, use `DATABASE ENGINE DUCKDB` (4.1), not `SET DATABASE ENGINE`.

### 4.9.1 SET SQL_FATAL_ERRORS

```
SET SQL_FATAL_ERRORS ON | OFF
```

`ON` (default): a database error stops the program, or jumps to the `ON ERROR` handler. `OFF`: the error sets `ERR`/`ERRMSG$` and execution continues. Any other argument raises `Expected ON or OFF after SET SQL_FATAL_ERRORS`. See 4.8.

### 4.9.2 SET HASH_KEYS

```
SET HASH_KEYS PRESERVE_CASE | IGNORE_CASE
```

Sets `hash_keys_mode` (default `PRESERVE_CASE`). With `IGNORE_CASE`, keys of hashes built from parsed JSON data are upper-cased, and sort keys are normalised. Chapter 1 has the details. This setting does not affect `FOR row IN (SELECT ...)` hashes: their column keys are always upper-cased. Any other argument raises `Expected PRESERVE_CASE or IGNORE_CASE after SET HASH_KEYS`.

### 4.9.3 SET NULL_HANDLING

```
SET NULL_HANDLING TO option
SET NULL_HANDLING FOR "column" TO option
SET NULL_HANDLING FOR "table.column" TO option
```

| Option | Effect on `LOAD` |
|---|---|
| `NULL` or `CONVERT_EMPTY_TO_NULL` | An empty field, or one containing only spaces, is stored as SQL `NULL`. **This is the default.** |
| `EMPTY` or `PRESERVE_EMPTY_STRINGS` | The field is stored as text: `''`, or the spaces as read. |

The setting decides what `LOAD` (every format) stores for empty fields. It is applied to each row after the `transform`/`validate` rules and the `TRANSFORM`/`VALIDATE ... WITH` functions, just before the row is inserted. Only text values are affected. Numbers, booleans and values that are already `NULL` pass through unchanged.

- **Precedence:** a rule `FOR "table.column"` wins over one `FOR "column"`, which wins over the global `SET NULL_HANDLING TO`. Names are not case-sensitive.
- **Scope:** settings last until changed, for the rest of the program.
- **Why NULL is the default:** SQL aggregates ignore `NULL` but count `''`, so `AVG` and `COUNT` give the right answers. DuckDB can also load an empty field into a typed column such as `INTEGER`, which fails with `''`.

Given `people.csv`:

```
id,first,middle,salary
1,Ann,,50000
2,Bob,J,
3,Cy,,61000
```

```basic
DATABASE OPEN ":memory:"
LOAD CSV "people.csv" CREATE TABLE p1 OPTIONS "header=true"
SELECT COUNT(middle) AS cnt_mid, AVG(salary) AS avg_sal FROM p1;
SET NULL_HANDLING FOR "middle" TO EMPTY
LOAD CSV "people.csv" CREATE TABLE p2 OPTIONS "header=true"
SELECT SUM(middle IS NULL) AS mid_nulls, SUM(salary IS NULL) AS sal_nulls FROM p2;
```

```
3 records loaded into table p1
+---------+---------+
| cnt_mid | avg_sal |
+---------+---------+
| 1       | 55500.0 |
+---------+---------+
(1 rows returned)
3 records loaded into table p2
+-----------+-----------+
| mid_nulls | sal_nulls |
+-----------+-----------+
| 0         | 1         |
+-----------+-----------+
(1 rows returned)
```

With `SET NULL_HANDLING TO EMPTY` (the behaviour before this setting worked), the first query gives `cnt_mid` 3 and `avg_sal` 37000.0, because the empty salary is counted as 0.

### 4.9.4 SET EMAIL

```
SET EMAIL PROVIDER expr [APIKEY expr] [SENDER expr] [DOMAIN expr]
          [HOST expr] [PORT expr] [USER expr] [PASSWORD expr] [SECURITY expr]
```

Stores email provider settings for the `EMAIL` statement. Keyword/value pairs can appear in any order until the end of the statement. `PORT` is converted to an integer and `SECURITY` to upper case. Any other keyword raises `Unexpected keyword 'X' in SET EMAIL statement.`. When parsing finishes, `Email provider configured.` is written to stderr. Chapter 6 covers providers and the `EMAIL` statement.

### 4.9.5 SET OUTPUT

`SET OUTPUT` sets the global `OutputConfig` object (`g_output_config`), which has four fields:

| Field | Default | Values |
|---|---|---|
| `mode` | `CONSOLE` | `CONSOLE`, `FILE`, `OFF` |
| `format` | `TEXT` | `TEXT`, `CSV`, `JSON`, `JSONL`, `XML`, `HTML`, `FIXED`, `EXCEL`, `SQL`, `PARQUET`, `PLAIN` |
| `file_path` | `""` | the target file for `FILE` mode |
| `sql_options` | `{}` | options parsed from `OPTIONS` (used by all formats despite the name) |

This configuration controls only **result sets**: line SQL queries, queries inside `EXECUTE` (SQLite), and `DESCRIBE`. `PRINT`, `WRITE`, `ECHO` and `SHOW` always write to the console (or to a file handle) and are not affected.

**Mode part** (optional):

| Clause | Effect |
|---|---|
| `CONSOLE` | mode = `CONSOLE` **and format reset to `TEXT`** (before any `FORMAT` clause on the same statement is applied) |
| `FILE expr` | mode = `FILE`, `file_path` = value of `expr`. The format is unchanged unless `FORMAT` follows. |
| `OFF` | mode = `OFF`. Line-level `SELECT`/`WITH`/`SUMMARIZE`/`PRAGMA` statements are **skipped entirely, not executed**. `EXECUTE` and `DESCRIBE` still run, but their output is discarded. |
| *(omitted, i.e. `SET OUTPUT FORMAT ...`)* | mode is set to `CONSOLE`. This turns off `FILE` or `OFF` mode. |

Any other word raises `Unknown output mode: X`.

**FORMAT part** (optional): `FORMAT name` sets the format. An unknown name raises `Unknown format type 'X'`. The word `TABLE` gives `Missing or invalid format type after FORMAT`. Each `FORMAT` clause **clears the previous options**. If the format is `SQL`, one of the words `INSERT`, `UPDATE`, `MERGE`, `REPLACE`, `UPSERT` can follow and is stored as `mode`.

**OPTIONS part** (optional, valid only after `FORMAT`): `OPTIONS string_expr`. The string is scanned for `key=value` pairs. Keys are words matched by `\b(\w+)=` and lower-cased. Each value runs up to the next `key=` and is stripped of spaces, commas and quotes. Values can therefore contain spaces (`title=Customer List`), but cannot contain another `word=` sequence.

```basic
SET OUTPUT FILE "out.csv" FORMAT CSV
SET OUTPUT FORMAT TEXT OPTIONS "box_style=BOX"
SET OUTPUT FILE "report.html" FORMAT HTML OPTIONS "full=yes, title=Customer List, subtitle=All rows"
SET OUTPUT FILE "dump.sql" FORMAT SQL UPSERT OPTIONS "pk=id, target_tablename=customers"
SET OUTPUT OFF
SET OUTPUT CONSOLE
```

---

## 4.10 The output pipeline and output formats

Every result set (the rows plus the column names) goes through `_handle_output(results, column_names)`:

- **CONSOLE mode:** calls `_write_as_<format>(results, headers, sys.stdout, options)`. `EXCEL` raises `Excel output requires FILE mode...`. `PARQUET` raises `Parquet output requires FILE mode...`.
- **FILE mode:** for `EXCEL` and `PARQUET`, the writer opens `file_path` itself. For every other format, the file is opened with `open(file_path, "w", encoding="utf-8", newline='')`. After writing, the console shows `N rows written to <file>`.
- **OFF mode:** nothing is written.

**Each query overwrites the output file** because the file is opened in `"w"` mode every time. Two `SELECT`s in a row leave only the second result in the file. `EXCEL` is the exception: if the workbook exists, each query adds a **new sheet** to it.

```basic
CREATE TABLE c (id INTEGER, name TEXT);
INSERT INTO c VALUES (1, 'Ann'), (2, 'Bo');
SET OUTPUT FILE "out.csv" FORMAT CSV
SELECT * FROM c WHERE id = 1;
SELECT * FROM c WHERE id = 2;
PRINT "PRINT still goes to console"
SET OUTPUT OFF
SELECT * FROM c;
PRINT "after OFF"
SET OUTPUT FORMAT TEXT
SELECT COUNT(*) AS n FROM c;
```

Console output:

```
1 rows written to out.csv
1 rows written to out.csv
PRINT still goes to console
after OFF
+---+
| n |
+---+
| 2 |
+---+
(1 rows returned)
```

`out.csv` then contains only `id,name` / `2,Bo`.

A related trap: `SET OUTPUT FILE "out.json"` with no `FORMAT` keeps the current format. If that format is `TEXT`, the file contains an ASCII table, not JSON.

### 4.10.1 Format reference

Examples use this table:

```basic
CREATE TABLE c (id INTEGER PRIMARY KEY, name TEXT, note TEXT);
INSERT INTO c VALUES (1, 'Ann', 'a<b'), (2, 'O''Neil', NULL);
```

#### TEXT (default)

ASCII grid with a row-count footer (4.2.5).

| Option | Values | Effect |
|---|---|---|
| `box_style` | `ASCII` (default), `BOX` | `BOX` draws Unicode box characters |
| `header` | `false` | omits the top border and header row |
| `footer` | `false` | omits the bottom border and `(n rows returned)` (also suppresses `(0 rows returned)`) |

`SET OUTPUT FORMAT TEXT OPTIONS "box_style=BOX"`:

```
┌────┬────────┬──────┐
│ id │  name  │ note │
├────┼────────┼──────┤
│ 1  │ Ann    │ a<b  │
│ 2  │ O'Neil │ NULL │
└────┴────────┴──────┘
(2 rows returned)
```

`OPTIONS "header=false, footer=false"`:

```
| 1  | Ann    | a<b  |
| 2  | O'Neil | NULL |
```

#### CSV

Python `csv.writer` with default settings: comma-delimited, minimal quoting, `\r\n` line endings. NULL is written as an empty field. Option `header=false` omits the header row.

```
id,name,note
1,Ann,a<b
2,O'Neil,
```

#### JSON

A JSON array of objects (`indent=2`). NULL becomes `null`. No newline is written after the closing `]`.

```
[
  {
    "id": 1,
    "name": "Ann",
    "note": "a<b"
  },
  {
    "id": 2,
    "name": "O'Neil",
    "note": null
  }
]
```

Values must be JSON-serialisable. DuckDB `DATE`, `TIMESTAMP` and `DECIMAL` values are not, and fail with `Object of type date is not JSON serializable`. Cast them to `VARCHAR`/`DOUBLE` in the query. SQLite returns dates as text, so this does not happen there.

#### JSONL

One compact JSON object per line. The same serialisation rules as JSON apply.

```
{"id": 1, "name": "Ann", "note": "a<b"}
{"id": 2, "name": "O'Neil", "note": null}
```

#### XML

A `<resultset>` of `<record>` elements, with one child element per column. `&`, `<` and `>` are escaped. NULL becomes an empty element. Column names are used as element names as they are, so they must be valid XML names.

```
<?xml version="1.0" encoding="UTF-8"?>
<resultset>
  <record>
    <id>1</id>
    <name>Ann</name>
    <note>a&lt;b</note>
  </record>
  ...
</resultset>
```

#### HTML

By default, a bare `<table>` with `<thead>`/`<tbody>`. Cells are escaped and NULL is empty. An empty result produces nothing.

| Option | Effect |
|---|---|
| `full` | any non-empty value (even `false`) produces a complete HTML document with embedded CSS, `<title>`, an `<h1>` title and a footer paragraph |
| `title` | page `<title>` and `<h1>` (default `Query Result`) |
| `subtitle` | `<h2>` below the title |
| `footer` | footer paragraph text (default `(n rows returned)`) |

The `title`, `subtitle` and `footer` options apply only together with `full`.

#### FIXED

No header and no separators. Each column is left-justified and padded to the width of its widest value or header. Embedded newlines are replaced by spaces. NULL is blank.

```
1 Ann   a<b 
2 O'Neil    
```

#### PLAIN

Writes only the **first column** of each row, with no header or footer. NULL is written as nothing. Option `newline=false` suppresses the newline after each value. This is useful for writing out text that the query has already built, such as JSON or HTML.

```
Ann
O'Neil
```

#### SQL

Generates SQL statements that recreate the rows.

| Option | Meaning |
|---|---|
| `mode` | `insert` (default), `replace`, `update`, `upsert`, `merge`. It can also be given as a bare word after `FORMAT SQL`. |
| `tablename` | source table used for primary-key discovery. Default: the table in a simple `FROM` clause of the last SQL statement. |
| `target_tablename` | table name written into the output. Default: `tablename`. If no table can be determined, `mytable` is used and a warning is written to stderr. |
| `pk` | primary-key column for `update`/`upsert`/`merge`. For `update` it is looked up automatically from the source table, falling back to `rowid`. |
| `vendor` | `sqlite`/`duckdb` (default: the current engine), `mysql` (changes upsert syntax), `oracle` (changes merge syntax) |

String values are quoted with doubled embedded quotes. NULL becomes `NULL`. Identifiers that are reserved words, or that are not simple names, are double-quoted. In DuckDB, bracket quoting is never used. An empty result writes `-- (0 rows returned)`.

```
SET OUTPUT FORMAT SQL
INSERT INTO c (id, name, note) VALUES (1, 'Ann', 'a<b');
INSERT INTO c (id, name, note) VALUES (2, 'O''Neil', NULL);

SET OUTPUT FORMAT SQL UPDATE
UPDATE c SET name = 'Ann', note = 'a<b' WHERE id = 1;

SET OUTPUT FORMAT SQL REPLACE
INSERT OR REPLACE INTO c (id, name, note) VALUES (1, 'Ann', 'a<b');

SET OUTPUT FORMAT SQL OPTIONS "mode=upsert, pk=id, target_tablename=cust"
INSERT INTO cust (id, name, note) VALUES (1, 'Ann', 'a<b') ON CONFLICT (id) DO UPDATE SET name = excluded.name, note = excluded.note;

SET OUTPUT FORMAT SQL OPTIONS "mode=upsert, pk=id, vendor=mysql"
INSERT INTO c (id, name, note) VALUES (1, 'Ann', 'a<b') ON DUPLICATE KEY UPDATE name = VALUES(name), note = VALUES(note);

SET OUTPUT FORMAT SQL OPTIONS "mode=merge, pk=id"
MERGE INTO c T USING (VALUES (1, 'Ann', 'a<b')) AS S(id, name, note) ON (T.id = S.id)
   WHEN MATCHED THEN UPDATE SET T.name = S.name, T.note = S.note
   WHEN NOT MATCHED THEN INSERT (id, name, note) VALUES (S.id, S.name, S.note);
```

(One statement is shown per mode. The real output has one statement per row.)

In `update` mode, if the primary-key column is not in the result set, the program stops with an explanatory error. For example, `Automatic update failed: The result set lacks a 'rowid' column. You must specify ... OPTIONS "pk=column_name".`

#### EXCEL (FILE mode only)

Writes an `.xlsx` workbook with openpyxl. If the path does not end in `.xlsx`/`.xls`, `.xlsx` is appended. The output has:

- a bold white-on-blue header row
- numbers kept numeric, everything else converted to text, NULL as empty
- column widths fitted to the content (capped at 50)
- a frozen header row

If the file already exists, a **new sheet is added** to it. openpyxl renames duplicate sheet names, e.g. `Cust`, `Cust1`.

| Option | Effect |
|---|---|
| `sheetname` | sheet name (default `Query Results`) |
| `title`, `subtitle` | merged title rows above the header |
| `footer` | merged italic footer row |

`title`, `subtitle` and `footer` currently crash the writer (see 4.14).

#### PARQUET (FILE mode only)

Writes an Apache Parquet file with pyarrow. Column types are inferred from the Python values. An empty result writes an empty file with all-string columns.

```basic
SET OUTPUT FILE "out.parquet" FORMAT PARQUET
SELECT * FROM c;          ' -> 2 rows written to out.parquet   (id: int64, name: string)
```

---

## 4.11 SQL-side helper functions

On **SQLite** connections, `_init_db` registers extra scalar functions through `SqliteStringFunctions.register_all`. They can be used inside any SQL statement:

- `REVERSE`
- `STUFF`
- `LEFT$`
- `RIGHT$`
- `LPAD`
- `RPAD`
- `REPLICATE`
- `CHARINDEX`
- `STARTS_WITH`
- `ENDS_WITH`
- `INITCAP`
- `SPLIT_PART`
- `TRANSLATE`
- `SOUNDEX`
- `INSTR` (2, 3 or 4 arguments)

DuckDB connections do not get these functions. DuckDB already has native versions of most of them. See **Chapter 3** for their signatures and behaviour.

---

## 4.12 SQLite vs DuckDB: differences that matter

| Area | SQLite (default) | DuckDB |
|---|---|---|
| Transactions | autocommit (`isolation_level=None`); explicit `BEGIN`/`COMMIT`/`ROLLBACK` | autocommit; explicit transactions are also supported |
| Extra SQL functions | DbBasic helpers registered (4.11) | not registered; use DuckDB built-ins |
| `EXECUTE` with several statements | split by DbBasic; each `SELECT`/`WITH`/`PRAGMA` with at least one row is displayed | sent as one string; nothing is displayed |
| `SHOW TABLES` | from `sqlite_master` | from DuckDB `SHOW TABLES` |
| `SHOW INDEXES` | implemented | not implemented; always `No indexes found.` |
| `SHOW CREATE TABLE` | stored text from `sqlite_master` | regenerated by `duckdb_tables()` |
| `DESCRIBE` | `PRAGMA table_info` columns | DuckDB `DESCRIBE` columns |
| `SUMMARIZE` | not available | displayed as a query |
| `::` casts | n/a | supported |
| JSON/JSONL output | values are text/numbers | `DATE`/`TIMESTAMP`/`DECIMAL` values fail to serialise |
| `PRINT` of query values | ints/floats | `DECIMAL` arrives as `Decimal` (no leading sign space) |
| String literals | double-quoted text such as `"Active"` is treated as a string when no such column exists | double quotes always mean an identifier; use single quotes |
| `FORMAT SQL` default `vendor` | `sqlite` | `duckdb` (bracket identifier quoting is disabled) |

Use single-quoted SQL string literals in all code that must run on both engines.

---

## 4.13 Console output statements

These statements write to stdout or to an open file handle. They are **not** affected by `SET OUTPUT`.

### 4.13.1 PRINT

```
PRINT [#n,] [expr [{; | ,} expr ...] [; | ,]]
```

Values are formatted with `_format_output_value`:

- Numbers print without a trailing `.0` for whole values. Non-negative numbers get a **leading space** (the classic BASIC sign position). Negative numbers print their `-`.
- Strings print as they are.
- A **hash** prints as indented JSON (`indent=2`).
- An **array** prints as `[a, b, c]`. Each element uses the same number formatting, so numbers keep their leading space. A hash element prints as compact JSON.

Separators:

| Separator | Effect |
|---|---|
| `;` | values are joined with nothing between them. A `;` at the end of the statement suppresses the newline. |
| `,` | inserts a **tab character**. A trailing `,` still ends the line (it does not suppress the newline). |

`PRINT` on its own prints an empty line.

```basic
a = 5 : b = -3 : s$ = "txt"
PRINT "a="; a; " b="; b
PRINT a, b, s$
PRINT "no newline";
PRINT " - continued"
PRINT
PRINT 2.5; 1/3; 10/2
DIM arr(2)
arr(0) = 1 : arr(1) = "two"
PRINT arr
h.name$ = "Ann" : h.age = 30
PRINT h
PRINT "trailing comma",
PRINT "next"
```

Output (`→` marks a tab):

```
a= 5 b=-3
 5→-3→txt
no newline - continued

 2.5 0.3333333333333333 5
[ 1, two,  0]
{
  "name$": "Ann",
  "age": 30
}
trailing comma→
next
```

**File output:** `PRINT #n, ...` writes to the file opened with `OPEN ... AS #n` (Chapter 6). The line ends with `os.linesep`. Mixing `PRINT #n` with `WRITE #n` therefore mixes `\n` lines (on macOS/Linux) with `\r\n` lines (WRITE uses `csv` defaults).

```basic
OPEN "p.txt" FOR OUTPUT AS #1
PRINT #1, "line one"; 42
PRINT #1, "a", "b"
CLOSE #1
```

`p.txt` contains `line one 42\n` and `a\tb\n`.

### 4.13.2 PRINT USING

```
PRINT [#n,] USING mask_expr; expr [, expr ...] [;]
```

The mask is any string expression. Values are separated by **commas**. A trailing `;` suppresses the newline. `Formatter.format` walks the mask from left to right:

- Literal characters are copied to the output.
- When the walker reaches a character from `# 0 9 * ! & \ $ < > ^`, it tries to match a field. The next value is formatted into that field.
- **After the last value**, literal text is copied until the next field character, so `PRINT USING "Total: ### units"; 42` prints `Total:  42 units`. A mask with no values prints an empty line.
- **A numeric field directly followed by `%`** shows the value multiplied by 100: `PRINT USING "##.#%"; 0.256` prints `25.6%`.
- If there are more values than fields, the extra values are ignored. The mask is not reused.

**Numeric fields.** A field is a run of the characters `$ * # 0 9 , space`, optionally followed by `.` and more `#`/`0` characters, optionally followed by `^^^^`.

| Mask element | Meaning |
|---|---|
| `#` or `9` | digit position, blank-filled |
| `0` | digit position, zero-filled |
| `.` | decimal point. The number of `#`/`0` after it sets the decimal places. A `9` after the point is **not** part of the field. |
| `,` | thousands separator, printed only between digits |
| `**` (at the start) | fill leading blanks with `*` |
| `$` or `$$` (at the start, or after `**`) | floating dollar sign placed just before the first digit |
| `^^^^` | scientific notation `d.ddE+NN` |
| space | part of the numeric field (it widens it) |

- If the integer part overflows the field, all digits are printed. There is no `%` overflow marker.
- Rounding uses Python's round-half-to-even (`2.5` gives `2`, `3.5` gives `4`).
- A negative sign is placed in the position before the first digit.

**String fields:**

| Mask | Meaning |
|---|---|
| `!` | first character only |
| `&` | the whole string. `&&&&` left-justifies into a width equal to the number of `&`, without truncating. |
| `\  \` | fixed width = number of spaces + 2; truncates or pads (left-justified) |
| `>\  \` / `^\  \` / `<\  \` | right-justify / centre / left-justify in the backslash field |

A string formatted with a numeric mask is printed unchanged. A number given a `&` mask goes through the numeric formatter, and the `&` is printed as a literal (`42&`).

```basic
PRINT USING "[####.##]"; 1234.567
PRINT USING "[####.##]"; 88
PRINT USING "[####.##]"; -78.9
PRINT USING "[00000.00]"; 12.3
PRINT USING "[##,###,###.##]"; 1234567.891
PRINT USING "[******.##]"; 42.5
PRINT USING "[**$###.##]"; 9
PRINT USING "[**$###.##]"; -9
PRINT USING "[$$#,###.00]"; 1500.5
PRINT USING "[$####.##]"; 25
PRINT USING "[#.##^^^^]"; 123456
PRINT USING "[#.##^^^^]"; 0.000789
PRINT USING "[##.##]"; 12345.678
PRINT USING "[#####]"; 2.5
PRINT USING "[!]"; "Hello"
PRINT USING "[&&&&&&&&]"; "Hi"
PRINT USING "[\    \]"; "Hello World"
PRINT USING "[>\    \]"; "Hi"
PRINT USING "[^\    \]"; "Hi"
PRINT USING "Item: &  Qty: ##  Price: $##.00"; "Widget", 10, 49.99
PRINT USING "a=## b=##"; 1, 2;
PRINT " <- same line"
```

```
[1234.57]
[  88.00]
[ -78.90]
[00012.30]
[ 1,234,567.89]
[**42.50]
[**$9.00]
[*-$9.00]
[$1,500.50]
[  $25.00]
[1.23E+05]
[7.89E-04]
[12345.68]
[    2]
[H]
[Hi      ]
[Hello ]
[    Hi]
[  Hi  ]
Item: Widget  Qty: 10  Price: $49.99
a= 1 b= 2 <- same line
```

Literal text after the last value (the closing `]` here) is printed up to the next field character. A mask such as `"## ##"` is a **single** five-character field, because space is a numeric-field character. Separate numeric fields with some other literal character.

**File output:** `PRINT #n, USING mask; values` writes the same text as the console form, followed by the system line ending (`os.linesep`). A trailing `;` suppresses the line ending.

For formatting into a variable rather than printing, see `FORMAT$` in Chapter 3.

### 4.13.3 WRITE

```
WRITE [#n,] [expr [, expr ...]]
```

Writes the values as one CSV record using Python's `csv.writer`. Strings containing the delimiter, a quote or a newline are quoted, with embedded quotes doubled. Numbers are written bare, and whole floats are written as integers (`193.0` becomes `193`).

- **Console:** the record is built in a buffer, stripped, and printed with a normal newline. `WRITE` with no values prints an empty line.
- **File handle:** the record is written with the csv module's `\r\n` terminator. The handle's dialect options are used, as given by `OPEN ... AS #n WITH OPTIONS "delimiter=| quotechar=..."` (Chapter 6). If the handle is not open, the program stops with `File #n not open.`.

```basic
WRITE "x", 1, 1.5, "q,r"
OPEN "q.txt" FOR OUTPUT AS #2 WITH OPTIONS "delimiter=|"
WRITE #2, "a", "b c", 3
CLOSE #2
```

Console: `x,1,1.5,"q,r"`. `q.txt`: `a|b c|3\r\n`.

A typical export loop:

```basic
OPEN "export.csv" FOR OUTPUT AS #1
WRITE #1, "ID", "Product", "Price"
FOR row IN (SELECT * FROM products)
    WRITE #1, row.id, row.name, row.price
NEXT
CLOSE #1
```

### 4.13.4 ECHO

```
ECHO any text to end of line
```

Before tokenising, a pre-processing pass (`preprocess_echo_statements`) turns every line that **starts** with `ECHO` into `ECHO "<rest of line>"`. It doubles any embedded `"` characters. `ECHO` then prints the text **literally**: no expression evaluation, no interpolation, and characters such as `"`, `$`, `;` and `<` are kept. Whitespace right after `ECHO` and trailing whitespace are removed. `ECHO` alone prints an empty line. `ECHO` is useful for emitting HTML or template text.

```basic
ECHO This is <raw> "text" with $ and ;
ECHO
ECHO   indented echo
```

```
This is <raw> "text" with $ and ;

indented echo
```

`ECHO` is recognised only at the start of a line. Because the rest of the line is always turned into a string, you cannot write a `: statement` after it on the same line.

---

## 4.14 Implementation notes / discrepancies

These were found by reading `src/dbbasic.py` and running test scripts. They describe current behaviour, which may differ from the built-in `HELP` text and the older documents.

**SQL recognition and text handling**

1. **SQL statement termination** (fixed). Line-level SQL used to end at the first `;` in the source text, even inside `'...'` or a comment. It now skips string literals, quoted identifiers and comments (4.2.3).
2. **SQL is recognised only at the start of a line.** It is not recognised after `THEN`, after `:`, or after a label. Only one SQL statement is allowed per line.
3. **Keyword joining inside string literals** (fixed). Multi-word keyword rewrites used to change text inside strings and SQL literals (`'for each'` became `'FOREACH'`). They now apply only to code (4.2.2).
4. **`END TRANSACTION;`** (fixed). It was not recognised as SQL, because the keyword list held `'END TRANSACTION'` while the lexer sees the joined token `ENDTRANSACTION`. Joined keywords in SQL code are now also split back apart before the statement is sent, so `FOR EACH ROW` in a trigger reaches the engine intact.
5. **Bind-variable scanning** (fixed). It used to be purely textual, so `'x:y'`, `':memory:'` and DuckDB `::TYPE` casts were taken as variable references. A missing bind variable is fatal even with `SQL_FATAL_ERRORS OFF`.
6. **Numeric bind values are always floats**, so `SELECT :i` shows `1.0`.

**SET**

7. **Unknown `SET` options** (fixed). They used to be skipped silently, with the rest of the line run as a new statement (`SET DATABASE ENGINE DUCKDB` in `examples/setoutputsql.bas` only worked by accident, and `SET x = 5` was an assignment). They now raise `Unknown SET option`.
8. **`SET NULL_HANDLING`** (fixed). It had no effect: the settings were stored but never read, and the global form was not parsed. It now controls `LOAD`, with empty fields stored as `NULL` by default (4.9.3).
9. **`SET OUTPUT FORMAT TABLE`** (a `HELP SET OUTPUT` example) is rejected. The table format is called `TEXT`. The help's format list also leaves out `JSONL`, `XML`, `FIXED` and `PLAIN`.
10. **`SET OUTPUT FORMAT ...` without a mode forces `CONSOLE`**, which silently cancels an earlier `FILE` or `OFF`. `SET OUTPUT CONSOLE` resets the format to `TEXT`, and `FILE` without `FORMAT` keeps the old format.
11. **`SET OUTPUT OFF` does more than suppress output.** It prevents line-level `SELECT`/`WITH`/`SUMMARIZE`/`PRAGMA` statements from running at all. Side effects such as a `PRAGMA` setting, or `ERR` being reset, do not happen.

**Output writers**

12. **FILE mode overwrites the file on every query.** Only `EXCEL` appends, by adding a sheet.
13. **The HTML `full` option is true for any non-empty value**, including `full=false`.
14. **The Excel `title`, `subtitle` and `footer` options crash.** Merged cells cause `'MergedCell' object has no attribute 'column_letter'` during the column-width pass, and the workbook is not saved.
15. **JSON and JSONL output fail on DuckDB `DATE`/`TIMESTAMP`/`DECIMAL` values** with "not JSON serializable".
16. **The JSON writer prints no trailing newline.** CSV console output uses `\r\n` line endings.

**EXECUTE, SHOW and DESCRIBE**

17. **`EXECUTE` behaves differently on the two engines.** On DuckDB, multi-statement strings run but `SELECT` results are never displayed. On SQLite, empty results print nothing and `SUMMARIZE` is not treated as a query. `HELP EXECUTE` describes it as running BASIC code (`EXECUTE "PRINT 1 + 2"`), but it only runs SQL; dynamic BASIC is `EVAL`.
18. **`SHOW INDEXES` is not implemented for DuckDB.** The DuckDB branch is `pass`, so it always prints `No indexes found.`. `HELP SHOW INDEXES` shows `FROM "table"`, but the parser accepts `ON table`. A separate `_get_database_objects('indexes')` method contains DuckDB index SQL but `SHOW INDEXES` does not call it.
19. **`HELP SHOW CREATE TABLE` describes only the all-tables form.** The parser also accepts a single table name.
20. **`DESCRIBE` output does not match the older documents.** `docs/DbBasicCommandRerence.md` says `DESCRIBE` shows the `CREATE TABLE` statement. It actually shows `PRAGMA table_info` (SQLite) or `DESCRIBE` (DuckDB) output through the output pipeline. Use `SHOW CREATE TABLE` for the DDL.
21. **`HELP INSERT`/`HELP UPDATE` examples use double-quoted string literals** (`"System Start"`, `"Active"`). SQLite accepts these only as a fallback, and DuckDB treats them as identifiers.

**PRINT and PRINT USING**

22. **`PRINT USING` has several gaps:**
    - It prints an empty line when there are no values.
    - It does not reuse the mask for extra values.
    - It treats spaces as part of numeric fields.
    - It does not accept `9` after the decimal point.
    - It gives no overflow indicator.
23. **`PRINT #n, USING ...`** (fixed). Without a trailing `;` it crashed with `cannot access local variable 'parts'`, and with one it never wrote a line ending to the file.
24. **A trailing `,` in `PRINT` does not suppress the newline.** It emits a tab and then ends the line, unlike classic BASIC.
