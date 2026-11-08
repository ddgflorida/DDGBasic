# Chapter 5: Data Loading, Conversion & Analysis

This chapter covers getting data **into** DDGBasic from files: the `LOAD` statement and its options, the row-level transform and validation hooks, JSON/XML normalisation into related tables, the streaming `FOR ... IN` file loops, the `PARSEJSON` function, the `ANALYZE` family of profiling statements, and the `UPGRADE` statements that rewrite files to match a schema.

How to query loaded tables and how `SET OUTPUT` writes results back out to files are covered in **Chapter 4 (Database, SQL & Output)**. File handles, `READ FILE`, `FETCH` and `FOR ... IN FILES` are covered in **Chapter 6 (Files, System, Network & UI)**. User-defined `FUNCTION`s, `ON ERROR` and `EXIT FOR` are covered in **Chapter 2 (Control Flow & Procedures)**. Hashes, arrays and `SET HASH_KEYS` are covered in **Chapter 1 (Language Fundamentals)**.

All examples in this chapter were run against `src/ddgbasic.py`. The output shown is what the interpreter actually printed. Messages written to stderr (warnings, notices) are shown together with stdout.

## Contents

- [5.1 Overview](#51-overview)
- [5.2 LOAD statement syntax](#52-load-statement-syntax)
- [5.3 The destination clause](#53-the-destination-clause)
- [5.4 The OPTIONS string](#54-the-options-string)
  - [5.4.1 How the string is parsed](#541-how-the-string-is-parsed)
  - [5.4.2 Option reference](#542-option-reference)
- [5.5 Formats](#55-formats)
  - [5.5.1 LOAD CSV](#551-load-csv)
  - [5.5.2 LOAD FIXED](#552-load-fixed)
  - [5.5.3 LOAD TEXT](#553-load-text)
  - [5.5.4 LOAD JSON](#554-load-json)
  - [5.5.5 LOAD JSONL](#555-load-jsonl)
  - [5.5.6 LOAD XML](#556-load-xml)
  - [5.5.7 LOAD HTML](#557-load-html)
  - [5.5.8 LOAD EXCEL](#558-load-excel)
  - [5.5.9 LOAD PARQUET](#559-load-parquet)
- [5.6 Column selection and renaming (fields=)](#56-column-selection-and-renaming-fields)
- [5.7 Option-string transform and validate rules](#57-option-string-transform-and-validate-rules)
- [5.8 PROCESS_BY scripts](#58-process_by-scripts)
- [5.9 TRANSFORM / VALIDATE ... WITH fn clauses](#59-transform--validate--with-fn-clauses)
- [5.10 The load pipeline and rejected rows](#510-the-load-pipeline-and-rejected-rows)
- [5.11 LOAD CSV ... USING SCHEMA](#511-load-csv--using-schema)
- [5.12 Normalising JSON and XML into related tables](#512-normalising-json-and-xml-into-related-tables)
- [5.13 File-to-file format conversion](#513-file-to-file-format-conversion)
- [5.14 PARSEJSON](#514-parsejson)
- [5.15 FOR ... IN file loops](#515-for--in-file-loops)
- [5.16 ANALYZE statements](#516-analyze-statements)
- [5.17 UPGRADE statements](#517-upgrade-statements)
- [5.18 Notes](#518-notes)

---

## 5.1 Overview

| Statement | Purpose |
|---|---|
| `LOAD <format> file CREATE TABLE ... \| INTO TABLE ...` | Extract rows from a file, optionally transform/validate them, and insert them into a database table. |
| `FOR var IN CSV / JSON / JSONL / TEXT ...` | Iterate a file record by record in BASIC code, without a table. |
| `PARSEJSON(s$)` | Convert a JSON string to a hash/array value. |
| `ANALYZE CSV / FIXED / JSON / JSONL / TEXT / XML` | Profile a file: structure, consistency, type suggestions. Can save a schema. |
| `UPGRADE CSV / JSON / XML` | Rewrite files so they match a schema. |

The supported `LOAD` formats are `CSV`, `EXCEL`, `FIXED`, `JSON`, `JSONL`, `XML`, `HTML`, `TEXT` and `PARQUET`. Any other word after `LOAD` gives the error `Expected a valid LOAD type but got '...'`.

---

## 5.2 LOAD statement syntax

```
LOAD format filename_expr destination
     [OPTIONS options_expr]
     [TRANSFORM column WITH fn | TRANSFORM ROW WITH fn
      | VALIDATE column WITH fn | VALIDATE ROW WITH fn] ...
     [USING SCHEMA schema_file_expr]
```

The clauses must appear in this order:

1. **format**: one of the keywords listed above.
2. **filename_expr**: any string expression, such as a literal or a variable. `LOAD HTML` also accepts an `http://` or `https://` URL.
3. **destination**: `CREATE TABLE name` or `INTO TABLE name mode` (see [5.3](#53-the-destination-clause)). This clause is required.
4. **OPTIONS**: an optional string expression of `key=value` pairs (see [5.4](#54-the-options-string)).
5. **TRANSFORM / VALIDATE**: zero or more clauses (see [5.9](#59-transform--validate--with-fn-clauses)).
6. **USING SCHEMA**: optional, and only used by `LOAD CSV` (see [5.11](#511-load-csv--using-schema)).

A `LOAD` statement must be on one logical line. To split it across physical lines, end each line with the `_` continuation character (Chapter 1):

```basic
LOAD CSV "emp.csv" CREATE TABLE emp _
  OPTIONS "header=true" _
  TRANSFORM name WITH TRIM$
```

When the load finishes, `LOAD` prints `N records loaded into table T` (or `N records upserted into table T`). Any error inside the load sets `ERR = 1` and `ERRMSG$`, then raises a runtime error. You can trap that error with `ON ERROR` (Chapter 2).

---

## 5.3 The destination clause

```
CREATE [TABLE] table_name
INTO   [TABLE] table_name  [APPEND | TRUNCATE | IGNORE | UPSERT USING KEY key_expr]
```

`table_name` can be an unquoted identifier or a quoted string, for example `CREATE TABLE "my table"`. The word `TABLE` is optional in both forms, so `CREATE "customers"` and `INTO "customers" APPEND` are valid.

| Form | Behaviour |
|---|---|
| `CREATE TABLE t` | Creates `t` with one column per final header. Every column is `TEXT`, except a column named `_linenum`, which is `INTEGER`. If `t` already exists, the load fails with `Table 't' already exists. Use INTO TABLE ... TRUNCATE to overwrite.` |
| `INTO TABLE t APPEND` | Inserts into an existing table. The table must exist (`no such table: t`), and its column names must match the final headers. |
| `INTO TABLE t TRUNCATE` | Runs `DELETE FROM t`, then inserts. |
| `INTO TABLE t IGNORE` | Uses `INSERT OR IGNORE`, so rows that violate a unique or primary key constraint are skipped. The message gives the number of rows inserted and the number ignored. |
| `INTO TABLE t UPSERT USING KEY "col"` | Loads the rows into a temporary staging table. It then `UPDATE`s every row of `t` whose key matches, and `INSERT`s the rows whose key is not yet in `t`. `col` must be one of the final headers (case-sensitive). `t` does not need a unique constraint on `col`. |

With `INTO TABLE`, the mode keyword is optional. Without it, the rows are appended, as with `APPEND`.

`key_expr` is evaluated as an expression, so write the column name as a string literal: `USING KEY "id"`. An unquoted `id` would be read as a variable.

**Example: all four INTO modes**

```basic
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary TEXT, email TEXT);
LOAD CSV "emp.csv" INTO TABLE emp APPEND OPTIONS "header=true"
LOAD CSV "emp2.csv" INTO TABLE emp UPSERT USING KEY "id" OPTIONS "header=true"
SELECT id, name, salary FROM emp ORDER BY id;
LOAD CSV "emp2.csv" INTO TABLE emp IGNORE OPTIONS "header=true"
LOAD CSV "emp2.csv" INTO TABLE emp TRUNCATE OPTIONS "header=true"
SELECT id, name FROM emp;
```

Here `emp.csv` holds ids 1 to 4, and `emp2.csv` holds id 2 (changed) and id 5 (new).

```
4 records loaded into table emp
2 records upserted into table emp
+----+----------------+--------+
| id |      name      | salary |
+----+----------------+--------+
| 1  |   john smith   | 75000  |
| 2  | Jane Doe-Smith | 70000  |
| 3  | bob jones      | abc    |
| 4  | al brown       | 55000  |
| 5  | Eve Adams      | 90000  |
+----+----------------+--------+
(5 rows returned)
0 records loaded into table emp (2 ignored)
2 records loaded into table emp
+----+----------------+
| id |      name      |
+----+----------------+
| 2  | Jane Doe-Smith |
| 5  | Eve Adams      |
+----+----------------+
(2 rows returned)
```

Both rows of the `IGNORE` load were duplicates, so nothing was inserted.

**Transactions.** A LOAD writes all its rows or none: the inserts (or, for `UPSERT`, the staging, update and insert steps) run inside one transaction. If any insert fails, for example on a duplicate key with `APPEND`, the whole load is rolled back. Inside the program's own transaction (`BEGIN; ... COMMIT;`) the load becomes part of it, so a later `ROLLBACK` undoes it too. The `TRUNCATE` delete runs *before* that transaction starts, so it is not undone. A failed `CREATE TABLE` load drops the table it created.

**Short and long rows.** A row with fewer fields than the header is loaded with `NULL` in the missing columns. A row with more fields loses the extra ones. Both print a warning to stderr, for example `Warning: line 3 has 2 fields, expected 3; the missing fields are loaded as NULL.`

```
Runtime Error: An error occurred during the LOAD operation: UNIQUE constraint failed: emp.id at line 3, col 64.
```

---

## 5.4 The OPTIONS string

### 5.4.1 How the string is parsed

`OPTIONS` takes any string expression of `key=value` pairs. A key must come at the start or after a comma, semicolon or space. An unquoted value runs from just after its `=` to the next such key, and whitespace and commas at either end of it are removed. A value in `"..."` or `'...'` is taken exactly as written, so it can contain commas, semicolons and `word=` text; inside it, a doubled quote stands for one (`constraints="[x]:REGEX(a=b)"`, `sheetname='O''Brien'`). Keys are case-insensitive. All of these are equivalent:

```
"header=true, skip=2, delimiter=;"
"header=true skip=2 delimiter=;"
`header="true",skip='2',delimiter=;`
```

Because of this rule:

- A value can contain commas, so `fields=a,b,c` works.
- An unquoted value **must not contain a comma, semicolon or space followed by `word=`**, because that starts a new key. Quote such a value, for example `constraints="[x]:REGEX(a b=c)"`.
- Only the first `=` after a key matters. Repeating a key makes the later value win.
- Boolean options accept `true`, `1` or `y` (case-insensitive) as true. Anything else is false.

### 5.4.2 Option reference

These are every key the `LOAD` extractors and pipeline read. Unknown keys are ignored silently.

| Key | Formats | Default | Meaning |
|---|---|---|---|
| `header` | CSV | `auto` | `true`/`1`/`y` means the first row (after `skip`) holds column names. Any other value except `auto` means no header, and columns are named `C1`, `C2`, .... `auto` uses Python's `csv.Sniffer().has_header()` on the first 5 lines. |
| `header` | EXCEL, HTML | `true` | The first row holds column names. See [5.5.8](#558-load-excel) and [5.5.7](#557-load-html) for what happens with `false`. |
| `delimiter` | CSV | `auto` | The field separator. `auto` sniffs the first 8 KB for a comma, semicolon, tab or pipe, and falls back to `,`. |
| `encoding` | CSV, FIXED, TEXT, JSON, JSONL, HTML | `utf-8` | The Python codec name, for example `latin-1` or `cp1252`. TEXT opens with `errors='replace'`. The others fail on bad bytes. |
| `skip` | all except HTML | `0` | Physical lines to skip before reading. For JSON, XML and PARQUET it is the number of records to skip. For EXCEL it is the number of sheet rows. |
| `limit` | all except HTML | `-1` (no limit) | The maximum number of data records to read. |
| `fields` | CSV, EXCEL, JSONL | none | Column selection and renaming (see [5.6](#56-column-selection-and-renaming-fields)). |
| `fields` | FIXED | **required** | The column layout `name:start-end` or `name:start+length` (see [5.5.2](#552-load-fixed)). |
| `linenum` | TEXT, EXCEL, HTML | `false` | Adds an `INTEGER` column `_linenum` holding the source line or row number. |
| `skipblank` | TEXT | `false` | Drops lines that are empty or contain only whitespace. |
| `samplesize` | JSON, JSONL, XML | JSON: all records. JSONL and XML: `1000` | The number of records scanned to build the column list (the union of keys or child tags). |
| `record_path` | JSON | none | A dot path to the array to load, for example `data.rows`. |
| `record_tag` | XML | inferred | The repeating element that forms one row. |
| `attributes` | XML | `true` | Load the attributes of the record element as columns. `attributes=false` loads only its child elements, as before. |
| `element_type` | HTML | `TABLES` | `TABLES`, `LINKS` or `IMAGES` (case-insensitive). |
| `table_index` | HTML | `0` | Which `<table>` to load (0-based). |
| `source_url` | HTML | the filename | The value written into the `source` column. |
| `base_url` | HTML (LINKS, IMAGES) | `source_url` | The base used to resolve relative `<a href>` and `<img src>` values. |
| `sheetname` | EXCEL | none | The sheet to load. Matched exactly first, then case-insensitively. |
| `sheetindex` | EXCEL | `0` | The sheet to load by 0-based position, used when `sheetname` is not given. |
| `transform` | all (pipeline) | none | Option-string transform rules (see [5.7](#57-option-string-transform-and-validate-rules)). |
| `validate` | all (pipeline) | none | Option-string validation rules (see [5.7](#57-option-string-transform-and-validate-rules)). |
| `process_by` | all (pipeline) | none | The name of a string variable that holds a BASIC script run once per row (see [5.8](#58-process_by-scripts)). |
| `batchsize` | all (pipeline) | `10000` | Rows per `executemany` call. UPSERT always uses 10000. |
| `normalize` | JSON, XML | `false` | Normalise nested data into related tables (see [5.12](#512-normalising-json-and-xml-into-related-tables)). With any other format it gives the error `The NORMALIZE option is only supported for LOAD JSON and LOAD XML.` |

There is **no** `sheet` key (use `sheetname`), no `exclude` key for `fields`, and no `linenum` support for CSV, FIXED, JSON, JSONL, XML or PARQUET.

---

## 5.5 Formats

Every format extractor first produces a header list and then a series of data rows. The rows then go through the common pipeline described in [5.10](#510-the-load-pipeline-and-rejected-rows). With `CREATE TABLE`, every column is created as `TEXT`.

### 5.5.1 LOAD CSV

```
LOAD CSV file dest [OPTIONS "header=auto|true|false, delimiter=auto|c, skip=n, limit=n,
                              encoding=..., fields=..., transform=..., validate=...,
                              process_by=var, batchsize=n"]
```

The file is read with Python's `csv` module, so quoted fields, embedded commas and embedded newlines are handled. Header names are used exactly as written. Spaces are allowed because identifiers are quoted. Duplicate header names cause `duplicate column name: ...` when the table is created.

If a data row has **fewer** fields than the header, the missing fields are loaded as `NULL`. If a row has **more** fields, the extra fields are dropped. Both print a warning with the line number (see 5.3).

**Example: header detection and headerless files**

```basic
LOAD CSV "emp.csv" CREATE TABLE emp
SELECT * FROM emp;
LOAD CSV "cities.csv" CREATE TABLE cities
SELECT * FROM cities;
```

```
4 records loaded into table emp
+----+---------------+-------+---------+------------+
| id |     name      | dept  | salary  |   email    |
+----+---------------+-------+---------+------------+
| 1  |   john smith  | eng   | 75000   | john@x.com |
| 2  | jane doe      | mkt   | 65000.5 | NULL       |
| 3  | bob jones     | eng   | abc     | bob@x.com  |
| 4  | al brown      | sales | 55000   | al@x       |
+----+---------------+-------+---------+------------+
(4 rows returned)
3 records loaded into table cities
+----------+-------+----------+
|    C1    |  C2   |    C3    |
+----------+-------+----------+
| New York | USA   | 8400000  |
| London   | UK    | 8900000  |
| Tokyo    | Japan | 14000000 |
+----------+-------+----------+
(3 rows returned)
```

Using `header=false` on a file that does have a header loads the header line as data, in columns `C1..Cn`.

**Example: skip, delimiter and limit**

`semi.csv` has two title lines, then a semicolon-separated table:

```
Report title
Generated today
id;name;city
101;Alice;NYC
102;Bob;Chicago
```

```basic
LOAD CSV "semi.csv" CREATE TABLE c OPTIONS "header=true, skip=2, delimiter=;"
SELECT * FROM c;
```

```
2 records loaded into table c
+-----+-------+---------+
| id  | name  |  city   |
+-----+-------+---------+
| 101 | Alice | NYC     |
| 102 | Bob   | Chicago |
+-----+-------+---------+
(2 rows returned)
```

`encoding=latin-1` reads non-UTF-8 files correctly, so `Jos\xe9` is loaded as `José`.

### 5.5.2 LOAD FIXED

```
LOAD FIXED file dest OPTIONS "fields=name:start-end|name:start+length,..., [skip=n, limit=n, encoding=...]"
```

Positions are 1-based:

- `start-end` is **inclusive**: `1-5` means columns 1 to 5.
- `start+length` gives a start column and a width: `6+20` means columns 6 to 25.

Each value is stripped of leading and trailing whitespace. Blank source lines are skipped. A missing `fields` option gives the error `LOAD FIXED requires a 'fields' option specifying column positions.`

```basic
LOAD FIXED "people.fix" CREATE TABLE p OPTIONS "fields=id:1-5,name:6+20,dept:26-36,salary:37-41"
SELECT * FROM p;
```

```
3 records loaded into table p
+-------+-------------+-------------+--------+
|  id   |    name     |    dept     | salary |
+-------+-------------+-------------+--------+
| 00001 | John Smith  | Engineering | 75000  |
| 00002 | Jane Doe    | Marketing   | 65000  |
| 00003 | Bob Johnson | Sales       | 55000  |
+-------+-------------+-------------+--------+
(3 rows returned)
```

`ANALYZE FIXED` can guess a layout for you (see [5.16.2](#5162-analyze-fixed)).

### 5.5.3 LOAD TEXT

```
LOAD TEXT file dest [OPTIONS "linenum=true, skipblank=true, skip=n, limit=n, encoding=..."]
```

Each line becomes one row in a single column, `line_text`, with the line terminator removed. With `linenum=true`, a second column `_linenum` (INTEGER) holds the physical line number.

```basic
LOAD TEXT "notes.txt" CREATE TABLE n OPTIONS "linenum=true, skipblank=true"
SELECT * FROM n;
```

```
3 records loaded into table n
+----------------+----------+
|   line_text    | _linenum |
+----------------+----------+
| first line     | 1        |
|   third line   | 3        |
| last           | 4        |
+----------------+----------+
(3 rows returned)
```

### 5.5.4 LOAD JSON

```
LOAD JSON file dest [OPTIONS "record_path=a.b, samplesize=n, skip=n, limit=n, encoding=..., normalize=true"]
```

The whole file is parsed into memory. The extractor then decides which part of the document holds the records:

1. If `record_path` is given, it follows the dot-separated keys. If the path does not exist, it prints a message and continues with the whole document.
2. Otherwise, if the document is an object with exactly **one** key whose value is an array, that array is used. It prints `Notice: Automatically using single key ('k') as the record source.`
3. A single object is treated as a one-record array. Anything that is not an array of objects gives `The final JSON data to be loaded must be an array of objects.`

Columns are the union of keys across the first `samplesize` records, in the order first seen. Nested objects and arrays are stored as JSON text. Unlike the other formats, values keep their JSON types: missing keys and `null` become SQL `NULL`, and `true` is stored as `1`. Elements of the array that are not objects are skipped with a warning.

```basic
LOAD JSON "inv.json" CREATE TABLE inv
SELECT * FROM inv;
LOAD JSON "nested.json" CREATE TABLE r OPTIONS "record_path=data.rows"
SELECT * FROM r;
```

`inv.json` is `{"inventory": [ {...}, {...}, {...} ]}`. `nested.json` is `{"meta": {...}, "data": {"rows": [...]}}`.

```
Notice: Automatically using single key ('inventory') as the record source.
3 records loaded into table inv
+-----+---------+------+------------------+---------+--------+------------+
| id  | product | qty  |       dims       |  notes  | active |    tags    |
+-----+---------+------+------------------+---------+--------+------------+
| 101 | Widget  | 50   | {"w": 2, "h": 3} | NULL    | NULL   | NULL       |
| 102 | Gadget  | 75.0 | NULL             | On sale | 1      | NULL       |
| 103 | Thing   | NULL | NULL             | NULL    | NULL   | ["a", "b"] |
+-----+---------+------+------------------+---------+--------+------------+
(3 rows returned)
2 records loaded into table r
+---+---+
| a | b |
+---+---+
| 1 | x |
| 2 | y |
+---+---+
(2 rows returned)
```

`fields=` is **ignored** for JSON, with a warning. For relational loading of nested data, see `normalize=true` in [5.12](#512-normalising-json-and-xml-into-related-tables).

### 5.5.5 LOAD JSONL

```
LOAD JSONL file dest [OPTIONS "samplesize=n, fields=..., skip=n, limit=n, encoding=..."]
```

The file contains one JSON object per line. Headers are the union of keys in the first `samplesize` lines (default 1000). Keys that appear only after the sample are not loaded. Values are converted to strings: missing keys become `""`, whole-number floats lose their `.0`, and nested values become JSON text. Blank lines are skipped. A line that is invalid JSON, or that is not an object, is skipped with a warning to stderr giving its physical line number.

```basic
LOAD JSONL "events.jsonl" CREATE TABLE ev OPTIONS "fields=id,ev:event"
SELECT * FROM ev;
```

```
Warning: Skipping invalid JSON on line 4
Warning: Skipping non-object JSON on line 5
3 records loaded into table ev
+----+--------+
| id | event  |
+----+--------+
| 1  | login  |
| 2  | view   |
| 3  | logout |
+----+--------+
(3 rows returned)
```

### 5.5.6 LOAD XML

```
LOAD XML file dest [OPTIONS "record_tag=name, attributes=true|false, samplesize=n, skip=n, limit=n, normalize=true"]
```

Every element whose tag (with any namespace removed) equals `record_tag` becomes one row. Its **attributes** and its **child elements** become columns, taken as the union of the names in the first `samplesize` records. The attribute columns come first.

- A simple child becomes its text.
- A child that has attributes or children of its own is converted to a dictionary and stored as JSON text. Attributes become `@name` keys and mixed text becomes `#text`.
- A child that is missing from a record gives `""`.
- An attribute of the record element becomes a column of the same name, with any namespace prefix removed (`x:status` gives `status`). If a child element has the same name, the attribute column is called `name_attr`. `attributes=false` leaves attributes out.

If `record_tag` is omitted, the extractor infers it. It picks the child tag that most dominates its parent and occurs at least twice, and prints `Notice: 'record_tag' not specified. Inferred '<tag>'.` The file is parsed in streaming mode, so large files are fine.

```basic
LOAD XML "books.xml" CREATE TABLE books
SELECT * FROM books;
```

The source file is:

```xml
<catalog>
  <book id="b1"><title>Dune</title><author>Herbert</author><price>9.99</price></book>
  <book id="b2"><title>Emma</title><author>Austen</author>
        <price currency="GBP">5.50</price><year>1815</year></book>
</catalog>
```

```
Notice: 'record_tag' not specified. Inferred '<book>'.
2 records loaded into table books
+----+-------+---------+------------------------------------+------+
| id | title | author  |               price                | year |
+----+-------+---------+------------------------------------+------+
| b1 | Dune  | Herbert | 9.99                               | NULL |
| b2 | Emma  | Austen  | {"@currency": "GBP", "#text": 5.5} | 1815 |
+----+-------+---------+------------------------------------+------+
(2 rows returned)
```

The `id` attribute of `<book>` is the first column. Use `normalize=true` ([5.12](#512-normalising-json-and-xml-into-related-tables)) to turn nested elements into related tables.

### 5.5.7 LOAD HTML

```
LOAD HTML file_or_url dest [OPTIONS "element_type=TABLES|LINKS|IMAGES, table_index=n,
                                      header=true|false, linenum=true, source_url=..., base_url=...,
                                      encoding=..."]
```

The page is parsed with BeautifulSoup and the `lxml` parser, which must be installed. If the filename starts with `http://` or `https://`, the page is downloaded first. The request uses a browser User-Agent and a 15-second timeout, and prints `Notice: Fetching URL for LOAD HTML: ...`.

The `element_type` option decides what is extracted. It is an option, **not** a keyword: `LOAD HTML LINKS "f.html"` is a syntax error.

| `element_type` | Columns | Notes |
|---|---|---|
| `TABLES` (default) | `source`, then one column per header cell | Uses `<table>` number `table_index`. With `header=true`, the first `<tr>` (its `th` or `td` cells) supplies the names. Header names have `[` and `]` removed, and duplicates get `_2`, `_3`, and so on. Data cells are the `<td>` elements of each later row. |
| `LINKS` | `source`, `text`, `href` | Every `<a>` that has an `href`. `href` is resolved against `base_url`, which defaults to `source_url`. |
| `IMAGES` | `source`, `src`, `alt`, `title` | Every `<img>` that has a `src`. `src` is resolved against `base_url`, which defaults to `source_url`. |

The `source` column holds `source_url`, which defaults to the filename or URL.

```basic
LOAD HTML "page.html" CREATE TABLE ht OPTIONS "linenum=true"
SELECT * FROM ht;
LOAD HTML "page.html" CREATE TABLE lk OPTIONS "element_type=links, source_url=https://example.com/dir/page.html"
SELECT * FROM lk;
LOAD HTML "page.html" CREATE TABLE im OPTIONS "element_type=images, base_url=https://example.com/"
SELECT * FROM im;
```

```
2 records loaded into table ht
+-----------+-------+------+--------+----------+
|  source   | Name  | City | Name_2 | _linenum |
+-----------+-------+------+--------+----------+
| page.html | Alice | NYC  | A2     | 1        |
| page.html | Bob   | LA   | B2     | 2        |
+-----------+-------+------+--------+----------+
(2 rows returned)
2 records loaded into table lk
+-----------------------------------+----------+----------------+
|              source               |   text   |      href      |
+-----------------------------------+----------+----------------+
| https://example.com/dir/page.html | About us | /about.html    |
| https://example.com/dir/page.html | X        | https://x.org/ |
+-----------------------------------+----------+----------------+
(2 rows returned)
2 records loaded into table im
+-----------+----------------------------------+------+----------+
|  source   |               src                | alt  |  title   |
+-----------+----------------------------------+------+----------+
| page.html | https://example.com/img/logo.png | Logo | Our logo |
| page.html | http://cdn/x.gif                 | NULL | NULL     |
+-----------+----------------------------------+------+----------+
(2 rows returned)
```

The `<a>` without an `href` was ignored.

With `header=false`, the first row is data and the columns are named `C1..Cn` after the widest row. Shorter rows are padded with empty values, which become `NULL` by default:

```basic
LOAD HTML "page.html" CREATE TABLE ht2 OPTIONS "table_index=1, header=false"
SELECT * FROM ht2;
```

```
1 records loaded into table ht2
+-----------+--------+
|  source   |   C1   |
+-----------+--------+
| page.html | second |
+-----------+--------+
(1 rows returned)
```

### 5.5.8 LOAD EXCEL

```
LOAD EXCEL file dest [OPTIONS "sheetname=name | sheetindex=n, header=true, skip=n, limit=n,
                                linenum=true, fields=..., transform=..., ..."]
```

`.xlsx` files are read with `openpyxl`, which returns cached formula values (`data_only=True`). Any other extension is read with `xlrd3` as legacy `.xls`.

- The default sheet is the first one (`sheetindex=0`).
- Header cells are stripped. Empty header cells become `C1`, `C2`, ... by position.
- Whole-number floats are written without `.0`, and empty cells become `""`.
- `linenum=true` adds `_linenum`, which holds the physical sheet row number (1-based, counting skipped rows and the header row).

```basic
LOAD EXCEL "sales.xlsx" CREATE TABLE s1 _
  OPTIONS "sheetname=sales, linenum=true, fields=Product ID:pid,Sales Amount:amount, transform=trimall"
SELECT * FROM s1;
```

The sheet `Sales` has the headers `Product ID | Region | " Sales Amount "`. The case-insensitive sheet match finds it from `sales`.

```
3 records loaded into table s1
+-----+--------+
| pid | amount |
+-----+--------+
| 1   | 100    |
| 2   | 250.75 |
| 3   | 99     |
+-----+--------+
(3 rows returned)
```

With `header=false`, both `.xlsx` and `.xls` files produce `C1..Cn` columns, named after the first data row:

```basic
LOAD EXCEL "sales.xlsx" CREATE TABLE s2 OPTIONS "sheetindex=1, header=false, skip=1, limit=2"
SELECT * FROM s2;
```

```
2 records loaded into table s2
+----+--------+--------+
| C1 |   C2   |   C3   |
+----+--------+--------+
| 1  |  east  | 100    |
| 2  | west   | 250.75 |
+----+--------+--------+
(2 rows returned)
```

### 5.5.9 LOAD PARQUET

```
LOAD PARQUET file dest [OPTIONS "skip=n, limit=n, ..."]
```

The file is streamed batch by batch with `pyarrow`. Values are converted to strings, and struct or list values are written as JSON text. `NULL` is read as `""`, which is then stored as `NULL` by default (see `SET NULL_HANDLING`, [4.9.3](04-database-sql-and-output.md#493-set-null_handling)).

```basic
LOAD PARQUET "items.parquet" CREATE TABLE items
SELECT * FROM items;
```

The file has the columns `id`, `name`, `tags` (list of strings) and `price`.

```
3 records loaded into table items
+----+------+------------+-------+
| id | name |    tags    | price |
+----+------+------------+-------+
| 1  | a    | ["x"]      | 1.5   |
| 2  | b    | []         | 2.0   |
| 3  | NULL | ["y", "z"] | NULL  |
+----+------+------------+-------+
(3 rows returned)
```

The list column `tags` is stored as JSON text.

---

## 5.6 Column selection and renaming (`fields=`)

For **CSV, EXCEL and JSONL** only, `fields=` lists the source columns to keep, in output order. Each entry can rename its column:

```
fields=src1, src2:new_name, src3:
```

- Source names are matched **case-insensitively**. An unknown name gives the error `Field 'x' not found in source headers.`
- `src:new` renames the column. `src:` with an empty new name keeps the original name.
- Columns that are not listed are dropped. There is no exclude syntax.
- The new names are the column names used for `CREATE TABLE`, for `INTO TABLE` matching, and as the keys that later transform and validate steps see.

```basic
LOAD CSV "emp.csv" CREATE TABLE emp OPTIONS "header=true, fields=id:emp_id,name,salary:pay, transform=trimall;name:proper;pay:round(2)"
SELECT * FROM emp;
```

```
4 records loaded into table emp
+--------+------------+----------+
| emp_id |    name    |   pay    |
+--------+------------+----------+
| 1      | John Smith | 75000.00 |
| 2      | Jane Doe   | 65000.50 |
| 3      | Bob Jones  | 0.00     |
| 4      | Al Brown   | 55000.00 |
+--------+------------+----------+
(4 rows returned)
```

A `fields=[id] as emp_id` form is **not** supported and fails with `Field '[id] as emp_id' not found in source headers.`

---

## 5.7 Option-string transform and validate rules

These rules are written inside `OPTIONS`. They are the declarative way to clean data. They run before `process_by` and before the `WITH fn` clauses ([5.10](#510-the-load-pipeline-and-rejected-rows)).

### transform=

```
transform=rule;rule;...        where rule is  column:function   or a global keyword
```

Rules are separated by **semicolons**. Column names are case-insensitive and refer to the final (renamed) column names. Square brackets around a name are removed. A rule whose column does not exist prints `Warning: TRANSFORM rule for column 'x' will have no effect ...`.

| Rule | Effect |
|---|---|
| `trimall` | Strips whitespace from every column. |
| `upperall` / `lowerall` / `properall` | Upper-, lower- or title-cases every column. |
| `col:upper` / `col:lower` / `col:trim` / `col:proper` | Case or whitespace change for one column. |
| `col:round(n)` | Formats the value as a number with `n` decimals. Values that are empty or not numeric become `0.00...`. |
| `col:format(mask)` | Formats the value with the `PRINT USING` style formatter (Chapter 3), for example `format('#,##0.00')`. Values that are not numeric are passed through unchanged. |
| `col:date(IN,OUT)` | Re-formats a date. The mask tokens are `YYYY YY MM DD HH MI SS`. If parsing fails, the original value is kept. If `IN` has a time part and the full parse fails, the date part alone is tried. |

The rule is split at its first `:`, so masks can contain `:`, as in `date(YYYY-MM-DD HH:MI,DD/MM/YYYY HH:MI)`. Writing several rules separated by commas (`transform=trimall,State:upper`) is also wrong. It becomes a single rule for a column named `trimall,state`.

```basic
LOAD CSV "emp.csv" CREATE TABLE emp OPTIONS "header=true, transform=dept:upper;salary:format('#,##0.00')"
LOAD CSV "dates.csv" CREATE TABLE d OPTIONS "header=true, transform=joined:date(YYYY-MM-DD,MM/DD/YYYY);amount:round(1)"
```

```
+----+---------------+-------+-----------+------------+
| id |     name      | dept  |  salary   |   email    |
+----+---------------+-------+-----------+------------+
| 1  |   john smith  | ENG   | 75,000.00 | john@x.com |
| 2  | jane doe      | MKT   | 65,000.50 | NULL       |
| 3  | bob jones     | ENG   | abc       | bob@x.com  |
| 4  | al brown      | SALES | 55,000.00 | al@x       |
+----+---------------+-------+-----------+------------+
...
+----+------------------+--------+
| id |      joined      | amount |
+----+------------------+--------+
| 1  | 01/15/2024       | 3.1    |
| 2  | 15/02/2023       | 0.0    |
| 3  | 2022-12-01 10:30 | 0.0    |
+----+------------------+--------+
```

### validate=

```
validate=col:RULE[:RULE...];col:RULE...
```

Column names here are case-insensitive and refer to the final column names. Rule names are case-insensitive. Rules run in order. Only `REQUIRED` looks at empty values; every other rule ignores an empty value.

| Rule | Fails when |
|---|---|
| `REQUIRED` | The value is empty or contains only whitespace. |
| `ISINTEGER` | `int(value)` fails. |
| `ISNUMERIC` | `float(value)` fails. |
| `MINLENGTH(n)` / `MAXLENGTH(n)` | The length is less than or greater than `n`. |
| `IN(a,b,c)` | The value is not one of the listed items. Items are trimmed, and the comparison is case-sensitive. |
| `REGEX(pattern)` | Python `re.match` fails. The match is anchored at the start only. The pattern cannot contain `:` or `;`. |

A failing row is **dropped**. A message naming the physical line goes to stderr, and the load continues.

```basic
LOAD CSV "emp.csv" CREATE TABLE emp OPTIONS "header=true, validate=salary:ISNUMERIC;email:REQUIRED:REGEX(^[^@]+@[^@]+\.[a-z]+$)"
SELECT * FROM emp;
```

```
Validation failed on line 3: Column 'email' is REQUIRED but is empty.
Validation failed on line 4: Column 'salary' value 'abc' is not a number.
Validation failed on line 5: Column 'email' value 'al@x' does not match pattern '^[^@]+@[^@]+\.[a-z]+$'.
1 records loaded into table emp
+----+---------------+------+--------+------------+
| id |     name      | dept | salary |   email    |
+----+---------------+------+--------+------------+
| 1  |   john smith  | eng  | 75000  | john@x.com |
+----+---------------+------+--------+------------+
(1 rows returned)
```

---

## 5.8 PROCESS_BY scripts

`process_by=varname` names a **string variable** that holds BASIC source code. It must be a variable name, not the code itself. The code is executed once for every row that passes validation. While it runs, these variables are set:

| Variable | Content |
|---|---|
| `rec` | A hash of the current row, keyed by the final column names. |
| `physical_line_num` | The source line or row number. |
| `logical_line_num` | The data-record number, starting at 1. |

The script can change fields (`rec.name = ...`). Setting `rec.is_valid = 0` rejects the row. After the script runs, the row is rebuilt from `rec` in column order, so keys added to `rec` are not stored. The three variables are deleted afterwards. An unknown or non-string variable gives `PROCESS_BY variable 'x' not found or not a string.`

```basic
script$ = `
  rec.name = PROPER$(TRIM$(rec.name))
  IF NOT ISNUMERIC(rec.salary) THEN
    PRINT "Rejecting line"; physical_line_num; ": "; rec.name
    rec.is_valid = 0
  END IF
`
LOAD CSV "emp.csv" CREATE TABLE emp OPTIONS "header=true, process_by=script$"
SELECT id, name, salary FROM emp;
```

```
Rejecting line 4: Bob Jones
3 records loaded into table emp
+----+------------+---------+
| id |    name    | salary  |
+----+------------+---------+
| 1  | John Smith | 75000   |
| 2  | Jane Doe   | 65000.5 |
| 4  | Al Brown   | 55000   |
+----+------------+---------+
(3 rows returned)
```

---

## 5.9 TRANSFORM / VALIDATE ... WITH fn clauses

These clauses come after `OPTIONS`. They call a **user-defined `FUNCTION`** or a **built-in function** by name.

```
TRANSFORM column WITH fn      ' fn(cell)      -> new cell value
VALIDATE  column WITH fn      ' fn(cell)      -> falsy drops the row
TRANSFORM ROW    WITH fn      ' fn(row_hash)  -> new row hash (must return a hash)
VALIDATE  ROW    WITH fn      ' fn(row_hash)  -> falsy drops the row
```

- `column` is an identifier or a quoted string, for example `TRANSFORM "Product ID" WITH LCASE$`. It is matched case-insensitively against the final column names.
- Any number of clauses can be combined, in any order. When several `TRANSFORM` or `VALIDATE` clauses name the same column, the last one wins.
- `ROW` clauses are applied in the order written. Each `TRANSFORM ROW` receives the hash returned by the previous one. A `TRANSFORM ROW` function that returns something other than a hash gives the error `function must return a hash`.
- Function names are checked when the statement is parsed. An unknown name gives `TRANSFORM qty WITH: unknown function 'nofn'.` and nothing is loaded.
- Rows rejected by `VALIDATE ... WITH` are dropped **silently**. No message is printed.
- Values returned from BASIC functions keep their BASIC types. A number returned by a transform is stored as a float, so `75000` is stored as `75000.0` in a TEXT column.

```basic
FUNCTION clean_pay(v$)
  IF ISNUMERIC(v$) THEN clean_pay = VAL(v$) ELSE clean_pay = 0
END FUNCTION

FUNCTION has_email(e$)
  has_email = (INSTR(e$, "@") > 0)
END FUNCTION

FUNCTION add_band(r)
  IF VAL(r("salary")) >= 70000 THEN r("dept") = UCASE$(r("dept")) + "-SENIOR"
  add_band = r
END FUNCTION

FUNCTION not_sales(r)
  not_sales = (r("dept") <> "sales")
END FUNCTION

LOAD CSV "emp.csv" CREATE TABLE emp _
  OPTIONS "header=true" _
  TRANSFORM name WITH TRIM$ _
  TRANSFORM salary WITH clean_pay _
  VALIDATE email WITH has_email _
  TRANSFORM ROW WITH add_band _
  VALIDATE ROW WITH not_sales
SELECT * FROM emp;
```

```
2 records loaded into table emp
+----+------------+------------+---------+------------+
| id |    name    |    dept    | salary  |   email    |
+----+------------+------------+---------+------------+
| 1  | john smith | ENG-SENIOR | 75000.0 | john@x.com |
| 3  | bob jones  | eng        | 0.0     | bob@x.com  |
+----+------------+------------+---------+------------+
(2 rows returned)
```

Jane was dropped by `VALIDATE email` because her email is empty. Al was dropped by `VALIDATE ROW` because his department is `sales`.

---

## 5.10 The load pipeline and rejected rows

`_execute_load_pipeline` runs the same steps for every format except the `normalize` and `USING SCHEMA` paths:

1. **Extract headers** from the format extractor.
2. **Parse the option rules**: `transform`, `validate`, the `WITH` clauses and `process_by`.
3. **Apply `fields=`** (CSV, EXCEL and JSONL only). This builds the final headers and the column map. If no headers result, the load stops with `Could not determine any columns from the source file ...`.
4. **Prepare the database**: run `CREATE TABLE` (all TEXT, `_linenum` INTEGER) and/or `TRUNCATE`.
5. **For each row**, in this order:
   1. Select and reorder the columns according to the column map.
   2. Apply option `transform` rules: the global `trimall`/`upperall`/`lowerall`/`properall` first, then per-column rules.
   3. Apply option `validate` rules. A failure drops the row with a stderr message.
   4. Run the `process_by` script. `rec.is_valid = 0` drops the row silently.
   5. Apply `TRANSFORM col WITH fn`, then `VALIDATE col WITH fn`. A falsy result drops the row silently.
   6. Apply `TRANSFORM ROW WITH fn` in order, then `VALIDATE ROW WITH fn`. A falsy result drops the row silently.
   7. Apply `SET NULL_HANDLING`: in each column set to convert (the default), an empty or all-space text value becomes `NULL` ([4.9.3](04-database-sql-and-output.md#493-set-null_handling)). The `USING SCHEMA` and `normalize` paths apply it too.
6. **Insert** the rows in batches of `batchsize` inside one transaction, or upsert them through a staging table.

**Rejected rows** are never written to a side table or file. They are only left out of the count printed in `N records loaded`. To keep the rejects, write them somewhere yourself from a `process_by` script or a `VALIDATE` function. For example, `PRINT #n` to a reject file before returning false.

**Errors** are different from rejections. A database error such as a constraint violation or a field-count mismatch, an unreadable file, or a bad option aborts the whole statement. It rolls back the inserts, sets `ERR=1` and `ERRMSG$`, and raises a runtime error.

`LOAD` sets `ERR` to 0 and `ERRMSG$` to `""` when it starts, so `IF ERR <> 0` after a successful `LOAD` is false.

---

## 5.11 LOAD CSV ... USING SCHEMA

```
LOAD CSV file dest [OPTIONS "batchsize=n"] USING SCHEMA schema_file
```

This path loads a CSV through a *column schema* instead of the normal pipeline. The schema is a JSON file in one of two forms:

- an array of column objects, or
- an object `{"process_by": "...", "columns": [ ... ]}`. This is the format that `ANALYZE CSV ... SAVE SCHEMA TO` writes.

Each column object has these keys:

| Key | Meaning |
|---|---|
| `name` | The output column name. Defaults to `column_N`. |
| `source` | A **DDGBasic expression** evaluated for each row. The source CSV headers are available as variables. A header that clashes with a language keyword gets a `_` prefix. An empty `source` gives `""`. If the whole source is a single-quoted literal (`"'Active'"`), it is treated as a string constant. Inside larger expressions, write string literals with backticks, for example ``"name + `-` + id"``. Single quotes inside an expression cause a parse error. |
| `transform` | Pipe-separated rules applied to the result: `trim`, `upper`, `lower`, `proper`, `round(n)`, `format('mask')`, `formatdate('mask')`. |
| `analysis` | Ignored when loading. It is informational output from `ANALYZE CSV`. |

The top-level `process_by` (object form only) can be a variable name or inline code. It receives `rec` and `physical_line_num`, and `rec.is_valid = 0` drops the row.

On this path the source file is always read as comma-delimited UTF-8 with a header row. `OPTIONS` keys other than `batchsize` are not used, and the `TRANSFORM` and `VALIDATE ... WITH` clauses are ignored. With any format other than CSV, `USING SCHEMA` prints a warning and is ignored.

```json
[
  {"name": "customer_id", "source": "id"},
  {"name": "customer", "source": "name", "transform": "trim | proper"},
  {"name": "amount", "source": "amount", "transform": "format('#,##0.00')"},
  {"name": "region", "source": "region", "transform": "upper"},
  {"name": "status", "source": "'active'"},
  {"name": "label", "source": "name + `-` + id"}
]
```

```basic
LOAD CSV "batch/a.csv" CREATE TABLE t USING SCHEMA "up_schema.json"
SELECT * FROM t;
```

```
Loading 'batch/a.csv' into table 't' using schema...
2 records transformed and loaded into table t
+-------------+----------+--------+--------+--------+-------+
| customer_id | customer | amount | region | status | label |
+-------------+----------+--------+--------+--------+-------+
| 1           | Ann      | 10.50  | NULL   | active | ann-1 |
| 2           | Bob      | 20.00  | NULL   | active | bob-2 |
+-------------+----------+--------+--------+--------+-------+
(2 rows returned)
```

`a.csv` has no `region` column. A source that names a column missing from the file evaluates to `""`.

---

## 5.12 Normalising JSON and XML into related tables

```
LOAD JSON file CREATE TABLE root_name OPTIONS "normalize=true [, transform=..., validate=...]"
LOAD XML  file CREATE TABLE root_name OPTIONS "normalize=true"
```

With `normalize=true`, the file is parsed in full and handed to the `LegacyJsonNormalizer` class. XML is first converted to a dictionary with `xmltodict`, which turns numeric text into int or float. The normalizer then builds a set of related tables:

1. **Flatten** the document into a node list. A top-level object is wrapped in a one-element list.
2. **Upgrade** scalars that sit at paths elsewhere holding arrays into one-element lists, then flatten again.
3. **Discover tables.** Each array becomes a table. The top-level array gets `root_name`. Child tables are named from their path with a parent prefix where needed, for example `orders_items`, `person_phones` or `catalog_book`. An array of scalar values, such as `"tags": ["x", "y"]`, becomes a child table with one column named after the key (`person_tags`, column `tags`), one row per value.
4. **Discover columns.** Scalar values under an object become columns, named from the tail of their path: `ship/city` becomes `ship_city`, and an XML attribute `@id` becomes `book_id`. Types are `INTEGER`, `REAL` or `TEXT`. Any string value forces `TEXT`.
5. **Create tables.** Each table first runs `DROP TABLE IF EXISTS`, then is created with a primary key `pk_<table>` and, for child tables, a foreign key `fk_<parent> REFERENCES parent(pk_parent)` plus an index on it. Names that are reserved words, or that contain punctuation or a leading digit, are double-quoted.
6. **Insert rows**, assigning primary key values from one counter shared by all tables.

Afterwards it prints a row count for each table it created.

The destination mode is ignored on this path. `CREATE TABLE` does **not** fail when the table exists, because the existing table is dropped. `INTO TABLE` accepts a mode keyword, but the mode has no effect. `fields=`, `process_by`, `USING SCHEMA` and the `WITH` clauses are not used.

The normalizer supports a reduced set of option rules. In `transform=`: `trimall`, `upperall`, and per-column `upper`, `lower`, `trim` and `proper`, keyed by the generated column name, for example `customer` or `ship_city`. In `validate=`: `REQUIRED`, `MINLENGTH(n)` and `REGEX(p)`. A validation failure prints `Validation failed for table ... Skipping row.`, and the row is not inserted. Neither are its child rows, for example the `items` of a rejected order. Column names in `validate=` are case-insensitive.

**Example: JSON**

```json
[
 {"order_id": 1, "customer": "acme", "total": 25.5,
  "items": [{"sku": "A1", "qty": 2}, {"sku": "B7", "qty": 1}],
  "ship": {"city": "Boston", "zip": "02116"}},
 {"order_id": 2, "customer": "globex", "total": 10,
  "items": [{"sku": "C3", "qty": 5}],
  "ship": {"city": "Austin", "zip": "73301"}}
]
```

```basic
LOAD JSON "orders.json" CREATE TABLE orders OPTIONS "normalize=true, transform=customer:upper"
SELECT * FROM orders;
SELECT * FROM orders_items;
SHOW CREATE TABLE orders_items
```

```
Normalizing JSON...
Running the JSON normalizer...
  - Step 1: Flattening data structure...
  - Step 2: Analyzing structure and discovering schema...
  - Step 3: Creating database tables...
  - Step 4: Populating tables with data...
JSON normalizer finished.
  - Created 2 tables:
    * orders: 2 records
    * orders_items: 3 records
+-----------+----------+----------+-------+-----------+----------+
| pk_orders | order_id | customer | total | ship_city | ship_zip |
+-----------+----------+----------+-------+-----------+----------+
| 1         | 1        | ACME     | 25.5  | Boston    | 02116    |
| 2         | 2        | GLOBEX   | 10.0  | Austin    | 73301    |
+-----------+----------+----------+-------+-----------+----------+
(2 rows returned)
+-----------------+-----------+-----------+-----------+
| pk_orders_items | items_sku | items_qty | fk_orders |
+-----------------+-----------+-----------+-----------+
| 3               | A1        | 2         | 1         |
| 4               | B7        | 1         | 1         |
| 5               | C3        | 5         | 2         |
+-----------------+-----------+-----------+-----------+
(3 rows returned)
CREATE TABLE orders_items (pk_orders_items INTEGER NOT NULL PRIMARY KEY, items_sku TEXT, items_qty INTEGER, fk_orders INTEGER REFERENCES orders(pk_orders));
```

Join the tables with `orders.pk_orders = orders_items.fk_orders`. The nested `ship` object was flattened into columns of `orders`, because it is an object and not an array.

**Example: XML** (the `books.xml` from [5.5.6](#556-load-xml))

```basic
LOAD XML "books.xml" CREATE TABLE catalog OPTIONS "normalize=true"
SELECT * FROM catalog_book;
```

```
+-----------------+---------+------------+-------------+------------+----------------+-------+-----------+------------+
| pk_catalog_book | book_id | book_title | book_author | book_price | price_currency | price | book_year | fk_catalog |
+-----------------+---------+------------+-------------+------------+----------------+-------+-----------+------------+
| 2               | b1      | Dune       | Herbert     | 9.99       | NULL           | NULL  | NULL      | 1          |
| 3               | b2      | Emma       | Austen      | NULL       | GBP            | 5.5   | 1815      | 1          |
+-----------------+---------+------------+-------------+------------+----------------+-------+-----------+------------+
```

The root element becomes a table, `catalog`, that has only its primary key. Attributes are preserved here, unlike in the flat `LOAD XML`. An element that has both an attribute and text, such as `<price currency="GBP">`, is split into separate columns (`price_currency` and `price`).

---

## 5.13 File-to-file format conversion

DDGBasic has no single "convert" statement. To convert a file, you `LOAD` it into a table and then `SELECT` it with output redirected to a file in the target format. Chapter 4 documents `SET OUTPUT FILE ... FORMAT` in full, including the TEXT, CSV, JSON, JSONL, XML, HTML, FIXED, EXCEL, SQL, PARQUET and PLAIN formats and their options.

```basic
LOAD CSV "emp.csv" CREATE TABLE emp OPTIONS "header=true, transform=trimall;name:proper"
SET OUTPUT FILE "emp.json" FORMAT JSON
SELECT id, name, dept FROM emp WHERE dept = 'eng';
SET OUTPUT FILE "emp.jsonl" FORMAT JSONL
SELECT id, name FROM emp;
SET OUTPUT CONSOLE FORMAT TEXT

LOAD JSON "emp.json" CREATE TABLE back
SET OUTPUT FILE "back.csv" FORMAT CSV
SELECT * FROM back;
SET OUTPUT CONSOLE FORMAT TEXT
```

```
4 records loaded into table emp
2 rows written to emp.json
4 rows written to emp.jsonl
2 records loaded into table back
2 rows written to back.csv
```

The resulting `emp.json` is:

```json
[
  {
    "id": "1",
    "name": "John Smith",
    "dept": "eng"
  },
  {
    "id": "3",
    "name": "Bob Jones",
    "dept": "eng"
  }
]
```

and `back.csv` is:

```
id,name,dept
1,John Smith,eng
3,Bob Jones,eng
```

Values loaded from CSV are TEXT, so the JSON output contains strings (`"id": "1"`). Use `CAST(id AS INTEGER)` in the `SELECT`, or create the table yourself with typed columns and load with `INTO TABLE ... APPEND`, to get numbers.

For row-by-row conversion without a table, combine `FOR ... IN CSV` ([5.15](#515-for--in-file-loops)) with `JSON_SERIALIZE$` (Chapter 3) and `PRINT #` (Chapter 6). `examples/csv2jsonl.bas` does exactly this.

---

## 5.14 PARSEJSON

```
value = PARSEJSON(json_string$)
```

`PARSEJSON` parses a JSON string and returns a DDGBasic value:

| JSON | DDGBasic value |
|---|---|
| object | hash. Keys are uppercased when `SET HASH_KEYS IGNORE_CASE` is active. |
| array | array (0-based) |
| `true` / `false` | `-1` / `0` |
| `null` | `""` |
| number / string | number / string |

An empty or whitespace-only string returns an empty hash. Invalid JSON raises `Invalid JSON string: ...`. Exactly one argument is required.

```basic
data = PARSEJSON("{""name"":""John"",""age"":30,""ok"":true,""n"":null,""scores"":[95,87]}")
PRINT data("name"); " "; data("age"); " "; data("ok"); " ["; data("n"); "] "; data("scores")(1)
PRINT data.name
e = PARSEJSON("")
PRINT HASH_COUNT(e)
l = PARSEJSON("[1,2,3]")
PRINT UBOUND(l)
```

```
John  30 -1 []  87
John
 0
 2
```

`PARSEJSON` is a function, not a statement: write `d = PARSEJSON(j$)`. There is no `PARSE JSON ... INTO` statement.

---

## 5.15 FOR ... IN file loops

```
FOR rec   IN CSV filename_expr [OPTIONS "..."]          ... NEXT [rec]
FOR rec   IN JSON(filename_expr)                        ... NEXT [rec]
FOR rec   IN JSONL(filename_expr)                       ... NEXT [rec]
FOR line$ IN TEXT(filename_expr)                        ... NEXT [line$]
```

These loops bind each record of a file to the loop variable and run the body once per record. The SQL form `FOR rec IN (SELECT ...)` is covered in Chapter 4, and `FOR f IN FILES(...)` in Chapter 6.

Behaviour common to all four loops:

- The filename must be a string, or the loop fails with `FOR...IN X requires a string filename.`
- Files are opened as UTF-8. Only the CSV loop takes an `encoding` option.
- The system variable `RECNO` holds the record number inside the loop, counting from 1.
- `EXIT FOR` leaves the loop (Chapter 2).
- When the loop ends, the loop variable is restored to its earlier value, or deleted if it did not exist before, and `RECNO` is restored to the value it had before the loop (so an outer loop's `RECNO` comes back), or deleted.

| Loop | Record value | Reading | `RECNO` |
|---|---|---|---|
| `CSV` | A hash. Keys `"1"`, `"2"`, ... hold the field by position. With `header=true`, header-name keys are added too. | Streams one row at a time. Blank lines are skipped. | 1, 2, ... (data rows; a header row is not counted) |
| `JSON` | A hash, converted as for `PARSEJSON`, with nested hashes and arrays. | The whole file is parsed. It must be an array of objects or a single object. An empty array skips the body. | 1, 2, ... |
| `JSONL` | Each line parsed, converted as for `PARSEJSON`. | Streams one line at a time. Blank lines are skipped. An invalid line is skipped with a warning. | the line number in the file (blank and skipped lines leave gaps) |
| `TEXT` | A string, the line without its `CR`/`LF`. | Streams. Invalid bytes are replaced. Blank lines are included. | 1, 2, ... |

**CSV loop details.** `OPTIONS` is parsed as for `LOAD` ([5.4.1](#541-how-the-string-is-parsed)) and takes `header=`, `delimiter=` (including `tab` and `auto`), `skip=` and `encoding=`, with the same meanings as for `LOAD CSV`. Other keys are ignored. The default is no header, and `header=auto` is not supported. Header names have every character other than `A-Z a-z 0-9 _` removed: `Product ID` becomes the key `ProductID`. Under `SET HASH_KEYS IGNORE_CASE`, they are also uppercased. The exact header text is a key too, so `rec("Product ID")` also works. Parentheses around the filename are optional, because they are simply a parenthesised expression.

```basic
FOR rec IN CSV "prices.csv" OPTIONS "header=true"
  PRINT RECNO; ": "; rec("ProductID"); " | "; rec("UnitPrice"); " | "; rec(3); " | "; rec.qty
NEXT
FOR rec IN CSV("prices.csv")
  PRINT RECNO; ": "; rec("1"); " / "; rec("2")
  IF RECNO = 3 THEN EXIT FOR
NEXT
FOR line$ IN TEXT("notes.txt")
  PRINT RECNO; "["; line$; "]"
NEXT
FOR r IN JSON("orders.json")
  PRINT RECNO; r("customer"); " items="; UBOUND(r("items")) + 1; " city="; r("ship")("city")
NEXT
FOR e IN JSONL("events.jsonl")
  PRINT RECNO; " "; e("ev")
  IF e("id") = 2 THEN EXIT FOR
NEXT
```

`prices.csv` is:

```
Product ID,Unit Price,qty
A1,9.99,2
B7,"1,250.00",1
```

```
 1: A1 | 9.99 | 2 | 2
 2: B7 | 1,250.00 | 1 | 1
 1: Product ID / Unit Price
 2: A1 / 9.99
 3: B7 / 1,250.00
 1[first line]
 2[]
 3[  third line  ]
 4[last]
 1acme items= 2 city=Boston
 2globex items= 1 city=Austin
 1 login
 3 view
```

Line 2 of `events.jsonl` is blank, so it is skipped. `RECNO` is the line number in the file, so the second record has `RECNO` 3. Without the `EXIT FOR`, the loop goes on to line 4, which is not valid JSON, skips it, and prints:

```
Warning: Skipping invalid JSON on line 4 of 'events.jsonl'
```

---

## 5.16 ANALYZE statements

`ANALYZE` reads a file and either prints a report or stores it in a hash. Every `ANALYZE` statement first resets `ERR = 0` and `ERRMSG$ = ""`. A file that cannot be found sets `ERR = 2` (TEXT, JSON, JSONL) or raises an error.

The `INTO` variable does not need to be declared first; it is set to a hash holding the report. Lists in a report, such as `ANALYZE CSV`'s `HEADERS`, are ordinary arrays.

### 5.16.1 ANALYZE CSV

```
ANALYZE CSV pattern_expr [OPTIONS "header=auto|true|false, delimiter=auto|c, limit=n,
                                   constraints=..., transform=..."]
                         [SAVE SCHEMA TO schema_file] [INTO hashvar]
```

The `OPTIONS`, `SAVE SCHEMA TO` and `INTO` clauses can appear in any order. `pattern_expr` is a glob. If it matches no file, you get `No files found matching pattern`.

**Single file.** The report covers:

- the detected delimiter;
- whether a header row is present (sniffed);
- the number of data records;
- the field-count distribution;
- statistics for each column.

For each column, a value is classified in this order:

1. empty;
2. **integer**, after removing `$` and `,`;
3. **float**;
4. **logical**: `true t y yes 1 false f n no 0`, case-insensitive;
5. **date**: one of the formats `%Y-%m-%d`, `%m/%d/%Y`, `%m-%d-%Y`, `%Y%m%d`, `%Y-%m-%dT%H:%M:%S`;
6. string.

The `SUGGESTED_DATA_TYPE` is `TEXT` if any string was seen. Otherwise, a column of dates (and empty fields) gives `DATE`, and dates mixed with numbers give `TEXT`. Otherwise it is `REAL` if any float, `INTEGER` if any integer or logical, and `TEXT` if the column is empty. Because integers are tested before dates, a value like `20230101` counts as an integer.

```basic
ANALYZE CSV "sales.csv"
```

```
--- CSV Analysis Report for: sales.csv ---
  Delimiter Detected : ','
  Header Row Detected: Yes
  Total Data Records : 4
  Field Count Distribution:
    - 4 record(s) with 6 field(s)

  Column Statistics:
    - [id] -> Suggested Type: INTEGER
      Length (Min/Max) : 1 / 1
      Value Range      : 1 to 4
    - [name] -> Suggested Type: TEXT
      Length (Min/Max) : 2 / 3
      Value Range      : "Ann" to "Dee"
    - [state] -> Suggested Type: TEXT
      Length (Min/Max) : 2 / 2
      Value Range      : "CA" to "TX"
    - [amount] -> Suggested Type: REAL
      Length (Min/Max) : 0 / 9
      Value Range      : 75.25 to 1200.5
    - [joined] -> Suggested Type: INTEGER
      Length (Min/Max) : 8 / 10
      Value Range      : 20230101 to 20230101
    - [active] -> Suggested Type: INTEGER
      Length (Min/Max) : 1 / 3
      Value Range      : 1 to 1
```

**INTO report hash (single file).** The keys are:

- `FILENAME`
- `DELIMITER`
- `HEADER_ROW` (-1 or 0)
- `DATA_RECORDS`
- `HEADERS`
- `FIELD_COUNT_DISTRIBUTION`: a hash of field count to number of rows
- `COLUMN_STATISTICS`: a hash with one entry per column, each holding `MIN_LEN`, `MAX_LEN`, `EMPTY_COUNT`, `INTEGER_COUNT`, `FLOAT_COUNT`, `DATE_COUNT`, `LOGICAL_COUNT`, `STRING_COUNT`, `MAX_DECIMALS`, `MIN_VALUE`, `MAX_VALUE` and `SUGGESTED_DATA_TYPE`

```basic
DIM rep AS HASH
ANALYZE CSV "sales.csv" INTO rep
PRINT rep("DELIMITER"); " "; rep("HEADER_ROW"); " "; rep("DATA_RECORDS")
cs = rep("COLUMN_STATISTICS")
s = cs("amount")
PRINT s("SUGGESTED_DATA_TYPE"); " "; s("FLOAT_COUNT"); " "; s("INTEGER_COUNT"); " "; s("EMPTY_COUNT"); " "; s("MAX_DECIMALS"); " "; s("MIN_VALUE"); " "; s("MAX_VALUE")
PRINT JSON_SERIALIZE$(rep("FIELD_COUNT_DISTRIBUTION"))
```

```
, -1  4
REAL  2  1  1  2  75.25  1200.5
{"6": 4}
```

`HEADERS` is an array of the column names in file order, so it can be indexed and passed to `UBOUND`.

**Constraints (single file only).** `constraints=[col]:RULE;[col]:RULE...` checks values before the statistics run. The rules are:

| Rule | Fails when |
|---|---|
| `REQUIRED` | The value is empty. |
| `ISDIGITS` | The value is not all digits. |
| `MINLENGTH(n)` / `MAXLENGTH(n)` | The length is out of range. |
| `REGEX(p)` | Python `re.match` fails. |
| `IN(a,b,...)` | The value is not one of the listed items. |
| `ISDATE(mask)` | The value does not match `mask`, which uses `MM`, `DD` and `YYYY`. |

Every rule except `REQUIRED` ignores empty values. If any constraint fails, only the list of violations is reported. With `INTO`, it is stored as `CONSTRAINT_FAILURES`, an array of `{LINE, COLUMN, VALUE, FAILED_RULE}`. No statistics are produced, and `SAVE SCHEMA` is skipped. With multiple files, constraints are ignored and a warning is printed.

```basic
ANALYZE CSV "sales.csv" OPTIONS "header=true, constraints=[state]:IN(CA,NY,FL);[name]:MINLENGTH(3);[joined]:ISDATE(YYYY-MM-DD)"
```

```
Constraint Violations found in 'sales.csv':
  - Line 3, Column 'joined': Value '01/15/2023' failed rule 'ISDATE(YYYY-MM-DD)'
  - Line 4, Column 'name': Value 'Cy' failed rule 'MINLENGTH(3)'
  - Line 4, Column 'state': Value 'TX' failed rule 'IN(CA,NY,FL)'
  - Line 5, Column 'joined': Value '20230101' failed rule 'ISDATE(YYYY-MM-DD)'
```

**Multiple files** (the pattern matches more than one file). The delimiter is sniffed from the first file and applied to all files. The report covers the consistency of delimiters, header presence and column sets, plus per-column aggregates with `PRESENT_IN_FILES`. The keys stored by `INTO` are `FILES_ANALYZED`, `FILE_LIST`, `TOTAL_RECORDS`, `IS_CONSISTENT`, `CONSISTENCY_DETAILS` and `COLUMN_STATISTICS`.

**SAVE SCHEMA TO** writes `{"process_by": "", "columns": [{name, source, transform, analysis:{suggested_type, max_len}}, ...]}`, with one entry per header, using the union of headers across files. A `transform=col:rule;...` option pre-fills the `transform` field of the matching columns. The schema can be used directly by `LOAD CSV ... USING SCHEMA` and by `UPGRADE CSV` ([5.17.1](#5171-upgrade-csv)).

```basic
ANALYZE CSV "batch/*.csv" SAVE SCHEMA TO "batch_schema.json" OPTIONS "transform=name:proper"
```

```
Notice: Auto-detected delimiter ',' from first file and applying it to all subsequent files.
--- Aggregated CSV Analysis Report for: batch/*.csv ---
  Files Analyzed          : 2
  Total Data Records      : 3
  Files Examined:
    - batch/a.csv
    - batch/b.csv

  --- Structural Consistency ---
  Overall Consistent      : No
  Delimiters Found        : ',' (2 files)
  Column Structures Found : 2
    - Structure #1 (1 files): ('id', 'name', 'amount')
    - Structure #2 (1 files): ('id', 'name', 'amount', 'region')

  --- Aggregated Column Statistics ---
    - [id] -> Suggested Type: INTEGER
      Present In         : 2 of 2 files
    - [name] -> Suggested Type: TEXT
      Present In         : 2 of 2 files
    - [amount] -> Suggested Type: REAL
      Present In         : 2 of 2 files
    - [region] -> Suggested Type: TEXT
      Present In         : 1 of 2 files
Schema definition saved to batch_schema.json
```

The saved file is shown here shortened:

```json
{
    "process_by": "",
    "columns": [
        {"name": "id", "source": "id", "transform": "",
         "analysis": {"suggested_type": "INTEGER", "max_len": 1}},
        {"name": "name", "source": "name", "transform": "proper",
         "analysis": {"suggested_type": "TEXT", "max_len": 3}},
        ...
    ]
}
```

### 5.16.2 ANALYZE FIXED

```
ANALYZE FIXED filename_expr [FIELDS "name:start-end|name:start+len,..."] [INTO hashvar]
```

Unlike `LOAD FIXED`, the layout here is given with a `FIELDS` keyword, not an option. Without `FIELDS`, the layout is guessed from the first 1000 lines: a column position counts as a separator if more than 90% of lines have a space there. Guessed fields are named `Field_1`, `Field_2`, .... The whole file is then streamed.

The printed report shows:

- the record count and maximum line length;
- a two-line column ruler and the first 5 lines of the file;
- for each field: position range, defined width, actual minimum and maximum length, empty count, and up to 3 sample values;
- a suggested `LOAD` command.

```basic
ANALYZE FIXED "emp.fix"
```

```
Notice: FIELDS clause not provided; guessing column layout for 'emp.fix'.
--- Fixed-Width Analysis Report for: emp.fix ---
  Total Records: 3
  Defined Fields: 4
  Maximum Line Length: 36

Position Reference:
        10        20        30
123456789012345678901234567890123456
00001 John Smith   Engineering 75000
00002 Jane Doe     Marketing   65000
00003 Bob Johnson  Sales       55000

  Field Analysis:
    [Field_1]:
      Position Range:  1-5
      Defined Width:   5
      Actual Length:   5 - 5
      Empty Fields: 0
      Sample Values: "00001", "00002", "00003"
    [Field_2]:
      Position Range:  7-17
      ...
    [Field_4]:
      Position Range:  32-36
      Defined Width:   5
      Actual Length:   5 - 5
      Empty Fields: 0
      Sample Values: "75000", "65000", "55000"

  Example LOAD Command:
    LOAD FIXED "emp.fix" CREATE TABLE MyTable OPTIONS "fields=Field_1:1-5,Field_2:7-17,Field_3:20-30,Field_4:32-36"
```

The suggested command can be copied and run as it is.

The `INTO` hash has the keys:

- `FILENAME`, `TOTAL_RECORDS`, `FIELD_COUNT`
- `LINE_LENGTH_DISTRIBUTION`
- `FIELD_ANALYSIS`: one entry per field, holding `START_POS` (0-based), `END_POS`, `DEFINED_WIDTH`, `MIN_LEN`, `MAX_LEN`, `EMPTY_COUNT` and `SAMPLE_VALUES`

```basic
DIM fr AS HASH
ANALYZE FIXED "emp.fix" FIELDS "id:1-5,name:7+12" INTO fr
PRINT fr("TOTAL_RECORDS"); fr("FIELD_COUNT")
fa = fr("FIELD_ANALYSIS")
n = fa("name")
PRINT n("START_POS"); n("END_POS"); n("DEFINED_WIDTH"); n("MIN_LEN"); n("MAX_LEN")
PRINT JSON_SERIALIZE$(n("SAMPLE_VALUES"))
```

```
 3 2
 6 18 12 8 11
["John Smith", "Jane Doe", "Bob Johnson"]
```

### 5.16.3 ANALYZE TEXT

```
ANALYZE TEXT filename_expr [INTO hashvar]
```

This reports on a plain text file:

- **Encoding**: `UTF-8 (with BOM)`, `UTF-8 (no BOM)`, or `ANSI / Western (e.g., Latin-1, CP-1252)` if the file does not decode as UTF-8.
- **Newline style**, from the first 8 KB: `CRLF (Windows)`, `LF (Unix/macOS)` or `N/A`.
- **Counts** of lines, empty lines, non-empty lines, characters and words.

The character count is taken after newline translation, so a CRLF file reports fewer characters than its byte size.

```basic
ANALYZE TEXT "crlf.txt"
DIM tr AS HASH
ANALYZE TEXT "notes.txt" INTO tr
FOR EACH k IN HASH tr
  PRINT k; "="; tr(k)
NEXT
```

```
--- Text File Analysis Report for: crlf.txt ---
  File Size       : 33 bytes
  Encoding        : UTF-8 (no BOM)
  Newline Style   : CRLF (Windows)
  Total Lines     : 3
  Empty Lines     : 1
  Total Chars     : 30
  Total Words     : 5
FILE_SIZE_BYTES= 32
ENCODING=UTF-8 (no BOM)
NEWLINE_TYPE=LF (Unix/macOS)
TOTAL_LINES= 4
EMPTY_LINES= 1
NON_EMPTY_LINES= 3
TOTAL_CHARACTERS= 32
TOTAL_WORDS= 5
```

### 5.16.4 ANALYZE JSON

```
ANALYZE JSON filename_or_pattern [INTO hashvar] [SAVE SCHEMA TO schema_file]
```

The `INTO` and `SAVE SCHEMA TO` clauses can appear in either order. If the name contains `*`, `?` or `[`, it is a glob: the records of every matching file are analysed together, the report adds `Files Analyzed`, and `INTO` also stores `FILE_COUNT`. No match gives `No files found matching pattern: ...` with `ERR = 2`. The file is treated as a list of records: a top-level object counts as one record. The report shows:

- the record count;
- whether all records have the same key set, with the distribution of key sets;
- a simplified structure tree. Arrays of objects are shown as a merged `[*]` object, and arrays of scalars by their first element `[0]`.

`INTO` stores `TOTAL_RECORDS`, `IS_CONSISTENT` (-1 or 0) and `KEY_SET_DISTRIBUTION`. The structure tree is only printed, never stored.

**SAVE SCHEMA TO** merges every record into a *superset* structure and writes it out as JSON. A leaf is replaced by its type name (`TEXT`, `INTEGER`, `REAL` or `BOOLEAN`). The first type seen for a key wins; `null` becomes `TEXT`. An array of objects becomes a one-element array holding the merged object schema. An array of scalars becomes `[]`. `UPGRADE JSON` is meant to consume this file.

```basic
ANALYZE JSON "users_a.json" SAVE SCHEMA TO "users_schema.json"
```

```
JSON Schema saved to users_schema.json
--- JSON Analysis Report for: users_a.json ---
  --- Consistency Check ---
  Total Records (Objects) : 2
  Is Consistent           : No
  Key Set Distribution:
    - 1 record(s) with keys: ('address', 'id', 'name', 'roles')
    - 1 record(s) with keys: ('active', 'address', 'email', 'id', 'name', 'roles')

  --- Simplified Structure ---
(Array)
  - [*]:        (Object)
         - "id": (Number)
         - "name": (String)
         - "address":            (Object)
             - "city": (String)
         - "roles":            (Array)
             - [*]:                   (Object)
                    - "r": (String)
                    - "since": (Number)
         - "email": (String)
         - "active": (Boolean)
```

`users_schema.json` contains:

```json
{
    "id": "INTEGER",
    "name": "TEXT",
    "address": {"city": "TEXT", "zip": "TEXT"},
    "roles": [{"r": "TEXT", "since": "INTEGER"}],
    "email": "TEXT",
    "active": "BOOLEAN"
}
```

With a wildcard, the files are merged into one schema: `ANALYZE JSON "data/*.json" SAVE SCHEMA TO "master.json"`.

### 5.16.5 ANALYZE JSONL

```
ANALYZE JSONL filename_expr [INTO hashvar]
```

The file is streamed line by line. Blank lines are skipped and not counted. The report shows the number of non-blank lines, how many are JSON objects (records), how many are invalid JSON, and how many are valid JSON but not an object (such as `"str"` or `[1, 2]`). It then shows structural consistency, the key-set distribution, and a structure tree built from the records. `INTO` stores `TOTAL_RECORDS` (non-blank lines), `VALID_JSON_RECORDS` (objects), `INVALID_JSON_RECORDS`, `NON_OBJECT_RECORDS`, `IS_CONSISTENT` and `KEY_SET_DISTRIBUTION` (keyed by the comma-separated key names).

```basic
ANALYZE JSONL "mixed.jsonl"
```

The file has 5 lines: `{"a":1,"b":2}`, `{"a":3}`, a blank line, `bad line`, and `"str"`.

```
--- JSONL Analysis Report for: mixed.jsonl ---
  --- Consistency Check ---
  Total Lines Read        : 4
  Valid JSON Objects      : 2
  Invalid JSON Lines      : 1
  Non-object JSON Lines   : 1
  Consistent Structure    : No
  Key Set Distribution:
    - 1 record(s) with keys: (a, b)
    - 1 record(s) with keys: (a)

  --- Simplified Structure ---
(Array)
  - [*]:        (Object)
         - "a": (Number)
         - "b": (Number)
```

### 5.16.6 ANALYZE XML

```
ANALYZE XML pattern_expr [SAVE SCHEMA TO schema_file] [INTO hashvar]
```

The two clauses can appear in either order. `pattern_expr` is a glob.

**Single file.** The report shows:

- the root element;
- the inferred record tag and how many times it occurs (the same heuristic as `LOAD XML`);
- any namespaces;
- a structure tree. A repeated element is shown with `[*]`, attributes as `@name (Attribute)`, and leaves as `<tag> (String|Number|...)`. If there is exactly one namespace, it is removed from the displayed names.

`INTO` stores `ROOT_ELEMENT`, `INFERRED_RECORD_TAG`, `RECORD_COUNT`, `NAMESPACES` and `STRUCTURE_TEXT`. Using `SAVE SCHEMA TO` with a single file is an error: `SAVE SCHEMA TO is only valid when analyzing multiple files with a wildcard.`

```basic
ANALYZE XML "books.xml"
DIM xr AS HASH
ANALYZE XML "books.xml" INTO xr
PRINT xr("ROOT_ELEMENT"); " "; xr("INFERRED_RECORD_TAG"); " "; xr("RECORD_COUNT")
```

```
--- XML Analysis Report for: books.xml ---
  Root Element            : <catalog>
  Inferred Record Tag     : <book> (2 instance(s))

  --- Simplified Structure ---
<catalog>
  <book [*]>
    @id (Attribute)
    <title> (String)
    <author> (String)
    <price> (String)
catalog book  2
```

**Multiple files.** All files are merged into a superset schema:

- Attributes and elements with the same name are unified as an element.
- Files whose roots differ but share the same repeating child are merged under the first root.
- Files with genuinely different structures are placed under a synthetic `virtual_root`.

The report shows each path with the number of files it occurs in. `SAVE SCHEMA TO` writes `{root: {...}}`, where every leaf is `""`. For multiple files, `INTO` stores `FILE_COUNT`, `ROOT_ELEMENT`, `INFERRED_RECORD_TAG` and `TAG_OCCURRENCES` (a hash from each path, such as `/orders/order`, to the number of files it occurs in).

```basic
ANALYZE XML "xml/*.xml" SAVE SCHEMA TO "orders_schema.json"
```

Here `o1.xml` uses `<order id="1">` with attributes, and `o2.xml` uses an `<id>` element plus an extra `<note>`.

```
Superset schema saved to orders_schema.json
--- XML Analysis Report for: xml/*.xml ---
  Files Analyzed          : 2
  Root Element            : <orders>
  Inferred Record Tag     : <order> (Based on first file)

  --- Consolidated Superset Schema (Occurrence) ---
- <orders> (2/2)
  - <order> (2/2)
    - <id> (2/2)
    - <customer> (2/2)
    - <total> (2/2)
    - <note> (1/2)
```

```json
{
  "orders": {
    "order": {
      "id": "",
      "customer": "",
      "total": "",
      "note": ""
    }
  }
}
```

---

## 5.17 UPGRADE statements

Each `UPGRADE` statement rewrites source files so that they match a schema. `UPGRADE` must be followed by `CSV`, `JSON` or `XML`. All three reset `ERR` and `ERRMSG$` at the start.

### 5.17.1 UPGRADE CSV

```
UPGRADE CSV source_pattern USING SCHEMA schema_file INTO output_folder
```

For every file matching the glob, `UPGRADE CSV` writes `output_folder/<same name>`, creating the folder if needed. It uses the same column-schema engine as `LOAD CSV ... USING SCHEMA` ([5.11](#511-load-csv--using-schema)): output columns, `source` expressions and pipe-separated `transform` rules. A file that fails is reported to stderr as `- Failed to upgrade 'x': ...` and the other files continue. If no file matches, a warning is printed and the statement returns.

The schema file can be the object written by `ANALYZE CSV ... SAVE SCHEMA TO` (`{"process_by": "...", "columns": [...]}`) or a plain **JSON array** of column objects. With the object form, `process_by` runs for each row, as in `LOAD CSV ... USING SCHEMA`. CSV values reach it as text, so compare with strings: `IF rec.id = "2" THEN rec.is_valid = 0`. A typical workflow is to analyse one file, edit the saved schema (rename, reorder or add columns, add `transform` rules or a `source` expression), then upgrade a whole batch:

```basic
ANALYZE CSV "batch/a.csv" SAVE SCHEMA TO "schema.json"
REM ... edit schema.json ...
UPGRADE CSV "batch/*.csv" USING SCHEMA "schema.json" INTO "out"
```

```basic
UPGRADE CSV "batch/*.csv" USING SCHEMA "up_schema.json" INTO "out"
```

This uses the `up_schema.json` from [5.11](#511-load-csv--using-schema).

```
Upgrading 2 CSV files...
Upgrade complete.
```

`out/a.csv`:

```
customer_id,customer,amount,region,status,label
1,Ann,10.50,,active,ann-1
2,Bob,20.00,,active,bob-2
```

`out/b.csv`:

```
customer_id,customer,amount,region,status,label
3,Cy,7.00,WEST,active,cy-3
```

Both files now have the same columns in the same order, even though `a.csv` had no `region` column.

### 5.17.2 UPGRADE JSON

```
UPGRADE JSON source_file USING SCHEMA schema_file INTO output_file
```

Rebuilds each record so it contains exactly the keys in the schema (for example, one written by `ANALYZE JSON ... SAVE SCHEMA TO`):

- Keys that are not in the schema are dropped.
- Missing leaves get defaults: `0` for INTEGER/REAL, `false` for BOOLEAN, `""` otherwise.
- Nested objects and arrays of objects are rebuilt recursively.
- A source that is an array produces an array; a single object produces a single object.
- The output is pretty-printed JSON.

```basic
DIM r AS HASH
ANALYZE JSON "in.json" SAVE SCHEMA TO "schema.json" INTO r
UPGRADE JSON "in.json" USING SCHEMA "schema.json" INTO "out.json"
PRINT "ERR="; ERR
```

With `in.json` containing `[{"name":"Ann","age":30},{"name":"Bob","tags":["x"]}]`, the saved schema is `{"name": "TEXT", "age": "INTEGER", "tags": []}`, and the run prints:

```
JSON Schema saved to schema.json
Upgrading JSON records from 'in.json'...
Upgrade complete. Saved to 'out.json'.
ERR= 0
```

`out.json` gives every record all three keys: Ann gets `"tags": []` and Bob gets `"age": 0`.

### 5.17.3 UPGRADE XML

```
UPGRADE XML source_pattern USING SCHEMA schema_file INTO output_folder
```

The schema is the `{root: {...}}` file written by multi-file `ANALYZE XML ... SAVE SCHEMA TO`. For each matching file, `UPGRADE XML` builds a new tree that follows the schema:

- Every schema element is emitted in schema order. An element missing from the source is created empty, for example `<note />`.
- Repeated source elements are repeated in the output.
- Source **attributes** whose names match schema elements are converted into child elements.
- Tag matching ignores case and namespace.
- Source data that does not appear in the schema is dropped.

The output is indented, has an XML declaration, and is written to `output_folder/<same name>`.

```basic
UPGRADE XML "xml/*.xml" USING SCHEMA "orders_schema.json" INTO "xml_out"
READ FILE "xml_out/o1.xml" INTO o$
PRINT o$
```

```
Upgrading 2 files...
Upgrade complete.
<?xml version='1.0' encoding='utf-8'?>
<orders>
  <order>
    <id>1</id>
    <customer>Acme</customer>
    <total>10</total>
    <note />
  </order>
  <order>
    <id>2</id>
    <customer>Globex</customer>
    <total>5</total>
    <note />
  </order>
</orders>
```

The `id` attribute from `o1.xml` became an `<id>` element, and the missing `<note>` was added.

---

## 5.18 Notes

This section collects details of how loading and analysis behave that are easy to miss.

**LOAD**

1. **There is no INTO-variable or TO-file destination.** The destination is always `CREATE [TABLE]` or `INTO [TABLE] ... APPEND|TRUNCATE|UPSERT|IGNORE`, so `LOAD` always targets a database table. To write files, use `SET OUTPUT` (5.13).
2. **`fields=` is ignored** for JSON, TEXT, XML, HTML and PARQUET (for FIXED it is the column layout). A warning is printed, for example `Warning: the fields option is ignored by LOAD JSON.`
3. **Only JSON keeps native value types.** `LOAD JSON` inserts values with their JSON types: `NULL` is used for missing keys and booleans become 1/0. All other formats insert strings. Empty fields are stored as `NULL` unless `SET NULL_HANDLING` says otherwise (4.9.3).
4. **Blank lines in a CSV file are skipped**, including a trailing blank line at the end of the file.

**Normalisation**

5. **Primary keys come from one shared counter** across all tables, so the keys of a child table do not start at 1.

**Loops**

6. **`FOR ... IN JSONL` does not check that a line is an object.** A line holding an array or a scalar is bound as an array or a scalar. A loop may want such lines; use `TYPENAME$` to tell them apart.
