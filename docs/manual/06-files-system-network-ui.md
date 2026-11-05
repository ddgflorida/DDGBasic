# Chapter 6: Files, System, Network & User Interface

This chapter covers the statements DbBasic uses to work with things outside the interpreter: text files, directories, archives, the operating-system shell, the console, HTTP services, e-mail and full-screen text applications.

Everything here is taken from the interpreter source (`src/dbbasic.py`, `src/dbscreen.py`). Where an example shows output, the script was run against the current interpreter. Statements that need a terminal UI, a GUI browser or a live mail server (`BROWSER`, `BELL`, sending with `EMAIL`) are described from the source only.

Related material in other chapters:

* File functions such as `FILE_EXISTS`, `FILESIZE`, `CURDIR$` and `ENVIRON$`: **Chapter 3, Built-in Functions**.
* `ON ERROR GOTO`, `ERR` and `ERRMSG$`: **Chapter 2, Control Flow & Procedures**.
* `PRINT` to the console, `PRINT USING`, `SET OUTPUT`, `SET SQL_FATAL_ERRORS`: **Chapter 4, Database, SQL & Output**.
* `LOAD`, `FOR ... IN CSV/JSON/JSONL/TEXT` loops and `ANALYZE`: **Chapter 5, Data Loading & Analysis**.

## Contents

1. [Sequential file I/O](#61-sequential-file-io)
   * [OPEN](#open) · [File handles and FREEFILE](#file-handles-and-freefile) · [PRINT #](#print-) · [WRITE / WRITE #](#write--write-) · [LINE INPUT #](#line-input-) · [EOF()](#eof) · [CLOSE](#close) · [READ FILE](#read-file) · [Complete example](#complete-sequential-file-example)
2. [File and directory management](#62-file-and-directory-management)
   * [FILES](#files) · [FOR ... IN FILES()](#for--in-files) · [COPY ... AS](#copy--as) · [NAME ... AS](#name--as) · [KILL](#kill) · [MKDIR](#mkdir) · [CHDIR](#chdir) · [RMDIR](#rmdir) · [Error codes](#error-codes-set-by-file-statements)
3. [Archives and hash unpacking](#63-archives-and-hash-unpacking)
   * [ZIP](#zip) · [UNZIP](#unzip) · [UNPACK](#unpack)
4. [System and console](#64-system-and-console)
   * [SHELL](#shell) · [BROWSER](#browser) · [BELL](#bell) · [INPUT](#input)
5. [HTTP: FETCH](#65-http-fetch)
6. [E-mail: SET EMAIL and EMAIL](#66-e-mail-set-email-and-email)
7. [Text screens](#67-text-screens)
   * [CLS, LOCATE, COLOR and BOX](#cls-locate-color-and-box) · [@ ... SAY ... GET](#--say--get) · [READ](#read) · [ALERT()](#alert) · [MENUBAR$()](#menubar) · [MENU()](#menu) · [BROWSE](#browse) · [EDIT RECORD](#edit-record) · [EDIT TEXT](#edit-text) · [VIEW](#view) · [SAVESCREEN and RESTSCREEN](#savescreen-and-restscreen) · [INKEY$ and LASTKEY$](#inkey-and-lastkey) · [Keyboard and terminal](#keyboard-and-terminal)
8. [TUI forms (archived)](#68-tui-forms-archived)
9. [Implementation notes / discrepancies](#69-implementation-notes--discrepancies)

---

## 6.1 Sequential file I/O

DbBasic uses the classic BASIC model: you open a file under a numbered handle (`#1`, `#2`, ...), read or write it line by line, then close it.

### OPEN

```
OPEN filename FOR {INPUT | OUTPUT | APPEND} AS #n [WITH OPTIONS "key=value key=value ..."]
```

| Part | Meaning |
|---|---|
| `filename` | Any string expression. A leading `~` is expanded to your home directory. |
| `INPUT` | Open an existing file for reading (Python mode `r`). |
| `OUTPUT` | Create the file, or truncate it if it exists (mode `w`). |
| `APPEND` | Open for writing at the end, creating the file if needed (mode `a`). |
| `#n` | Any numeric expression. It is truncated to an integer. |
| `WITH OPTIONS` | A string of space-separated `key=value` pairs. They are stored with the handle and passed to Python's `csv.writer` by `WRITE #n` (see below). Values are always strings, so only string-valued options such as `delimiter=;` or `quotechar='` are useful. A part without `=` raises a Python error. |

Behaviour:

* Files are always opened as UTF-8 text with `newline=''`, which means no newline translation happens.
* `OPEN` clears `ERR`/`ERRMSG$` first. If the file is missing (`INPUT` mode), `ERR` = 2 and `ERRMSG$` holds the OS message, and the Python `FileNotFoundError` is raised. You can catch it with `ON ERROR GOTO`.
* Opening a handle number that is already in use is a runtime error: `File #1 is already open.`
* Modes other than the three keywords (for example `BINARY` or `RANDOM`) give `Expected file mode`.

```basic
ON ERROR GOTO h
OPEN "nope.txt" FOR INPUT AS #1
PRINT "not here"
END
h:
PRINT "ERR="; ERR; " MSG="; ERRMSG$
```
```
ERR= 2 MSG=[Errno 2] No such file or directory: 'nope.txt'
```

### File handles and FREEFILE

Open files are held in a table keyed by integer handle number. `FREEFILE` (written without parentheses, or as `FREEFILE()`) returns the lowest positive handle number that is not in use, starting at 1. It takes no arguments.

```basic
n = FREEFILE
OPEN "out.txt" FOR OUTPUT AS #n
```

Handles are not closed automatically when an error occurs. Use `CLOSE` with no argument to close every open handle.

### PRINT #

```
PRINT #n, expression [{; | ,} expression ...] [;]
PRINT #n, USING format$; value [, value ...] [;]
```

This works like console `PRINT` (Chapter 4) but writes to handle `n`:

* `;` joins items with nothing between them and `,` puts a TAB between them.
* A trailing `;` suppresses the line ending.
* The line ending is `os.linesep`: `\n` on macOS/Linux and `\r\n` on Windows.
* A hash is written as indented JSON. An array is written as `[a, b, ...]`.
* Positive numbers get the usual leading space (`PRINT #1, 5` writes ` 5`).
* Printing to a handle that is not open is an error: `File #5 is not open.`

```basic
OPEN "out.txt" FOR OUTPUT AS #1
PRINT #1, "Hello, World!"
PRINT #1, "A"; "B", "C"
PRINT #1, "no newline";
PRINT #1, " - continued"
PRINT #1, USING "##.##"; 3.14159
CLOSE #1
```
Resulting file bytes: `Hello, World!\nAB\tC\nno newline - continued\n 3.14\n`

### WRITE / WRITE #

```
WRITE [#n,] expression [, expression ...]
```

`WRITE` writes one CSV record using Python's `csv.writer`:

* Values are separated by commas, or by the handle's `delimiter` option.
* Strings are quoted only when they need to be (`QUOTE_MINIMAL`).
* A float with no fractional part is written as an integer (`25.0` becomes `25`).
* Without `#n` the record goes to standard output, and the trailing record terminator is stripped before printing.
* With `#n`, the record ends with the system line ending (`os.linesep`), the same as `PRINT #n`.
* If the handle is not open: `File #n not open.`

```basic
WRITE "Name", "Age", 3.5, 42
OPEN "w.csv" FOR OUTPUT AS #1 WITH OPTIONS "delimiter=;"
WRITE #1, "Alice", 30, "New; York"
WRITE #1, "Bob", 25.0, "LA"
CLOSE #1
READ FILE "w.csv" INTO f$
PRINT f$
```
```
Name,Age,3.5,42
Alice;30;"New; York"
Bob;25;LA
```

### LINE INPUT #

```
LINE INPUT #n, var
```

Reads the next line from handle `n` and stores it in `var` after stripping trailing `\r`/`\n` characters.

* The value is always stored as a string, even when the variable name has no `$` suffix.
* At end of file it stores `""` and does not raise an error, so test `EOF(n)` before reading.
* If the handle is not open, the error is `File #n is not open.`
* There is no console form of `LINE INPUT`. Use `INPUT` for the console.

### EOF()

```
EOF(n)
```

Returns `-1` (true) if handle `n` is at end of file and `0` otherwise. It works by reading one character and seeking back. Called with no argument it returns `0`. If the handle is not open: `File #n is not open.`

### CLOSE

```
CLOSE #n      ' close one handle
CLOSE         ' close all open handles
```

`CLOSE #n` on a handle that is not open is a runtime error (`File #3 is not open.`).

### READ FILE

```
READ FILE filename INTO var$
```

Reads an entire UTF-8 text file into a string variable in one step.

* The destination name must end in `$`. Otherwise the error is `Destination for READ FILE must be a string variable.`
* A missing file sets `ERR` = 2 and raises `File not found: <name>`.

### Complete sequential-file example

```basic
n = FREEFILE
PRINT "FREEFILE ="; n
OPEN "out.txt" FOR OUTPUT AS #n
PRINT #n, "Hello, World!"
PRINT #n, "A"; "B", "C"
CLOSE #n
OPEN "out.txt" FOR INPUT AS #1
PRINT "Next FREEFILE ="; FREEFILE
WHILE NOT EOF(1)
  LINE INPUT #1, l$
  PRINT "["; l$; "]"
WEND
CLOSE #1
OPEN "out.txt" FOR APPEND AS #2
PRINT #2, "appended"
CLOSE
READ FILE "out.txt" INTO all$
PRINT all$
```
```
FREEFILE = 1
Next FREEFILE = 2
[Hello, World!]
[AB	C]
Hello, World!
AB	C
appended
```

(`examples/openfile.bas` and `examples/write.bas` in the repository show the same patterns.)

---

## 6.2 File and directory management

The statements in this section clear `ERR`/`ERRMSG$` before they run. Except where noted, they expand a leading `~` in paths.

### FILES

```
FILES [pattern] [INTO array] [RECURSIVE] [WITH DETAILS] [WITH FULLPATH] [WITH FILESONLY | WITH FOLDERSONLY]
```

Lists directory entries. The result is printed to the console, or stored in an array when you use `INTO`. The modifiers can appear in any order after the pattern.

| Part | Meaning |
|---|---|
| `pattern` | String expression. If it names a directory, every entry in it is listed (`dir/*`). Otherwise it is a glob pattern (`*`, `?`, `[...]`). If omitted, the default is `"."`. |
| `INTO array` | Store the results instead of printing them. The array must already exist (`DIM arr AS ARRAY`), or the error is `'arr' is not a dimensioned array.` The array is **replaced** by a plain list that starts at index 0. |
| `RECURSIVE` | Walk subdirectories (`os.walk`). The file-name part of the pattern is matched against file names in every directory. |
| `WITH DETAILS` | Printed form: name, size (or `<DIR>`) and modification time, separated by TABs. The name is padded to 25 characters, or to 70 with `WITH FULLPATH` or `RECURSIVE`. With `INTO`: each element is a hash with keys `name`, `size`, `date` (`YYYY-MM-DD HH:MM:SS`) and `isdir` (-1/0). |
| `WITH FULLPATH` | Report absolute paths instead of base names. |
| `WITH FILESONLY` / `WITH FOLDERSONLY` | Filter to files only or directories only. |

Behaviour notes:

* The output is sorted. In recursive mode it is sorted per directory: subdirectories of a directory come first, then its matching files.
* In **recursive** mode, directories are always included unless you add `WITH FILESONLY`, even when they do not match the pattern.
* If nothing matches, the printed form prints `File not found`. The recursive printed form prints `Directory not found` for a missing start directory. With `INTO`, the array is simply set to an empty list.
* `FILES` sets only `ERR` = 0. It does not clear `ERRMSG$`.

Example. The test tree is `ft/a.txt`, `ft/b.csv`, `ft/sub/c.txt`, `ft/sub/deep/d.txt`.

```basic
FILES "ft"
FILES "ft" WITH DETAILS
FILES "ft/*.txt" RECURSIVE
FILES "ft/*.xyz"
DIM arr AS ARRAY
FILES "ft" INTO arr
PRINT arr
PRINT "arr(0)="; arr(0); " UBOUND="; UBOUND(arr)
FILES "ft" INTO arr WITH DETAILS
PRINT arr(0).name; arr(0).size
FILES "ft/*.txt" INTO arr RECURSIVE WITH FILESONLY
PRINT arr
```
```
a.txt
b.csv
sub
a.txt                    	           2	2026-01-01 12:00:00
b.csv                    	           3	2026-01-01 12:00:00
sub                      	       <DIR>	2026-01-01 12:00:00
sub
a.txt
deep
c.txt
d.txt
File not found
[a.txt, b.csv, sub]
arr(0)=a.txt UBOUND= 2
a.txt 2
[a.txt, c.txt, d.txt]
```

### FOR ... IN FILES()

```
FOR var IN FILES(pattern [RECURSIVE] [WITH FULLPATH] [WITH FILESONLY | WITH FOLDERSONLY])
    ...
NEXT [var]
```

Runs the loop body once for each matching path. All modifiers go **inside** the parentheses. Any other token there is an error (`Unexpected token ... inside FILES().`).

* `pattern` must be a string. A directory name means "everything in it". With `RECURSIVE`, a directory becomes `dir/**/*`, and a pattern such as `ft/*.txt` becomes `ft/**/*.txt` (Python `glob` with `recursive=True`).
* Unlike `FILES RECURSIVE`, directories are filtered by the pattern here.
* Hidden (dot) files are skipped, as with any glob.
* The loop variable receives the base name, or the absolute path with `WITH FULLPATH`.
* Results are sorted by full path.
* If nothing matches, the body is skipped.
* `EXIT FOR` is supported.
* After the loop, the loop variable is restored to its previous value. If it did not exist before the loop, it is removed.

```basic
FOR f$ IN FILES("ft/*.txt" RECURSIVE)
  PRINT f$
NEXT
FOR f$ IN FILES("ft" WITH FULLPATH WITH FOLDERSONLY)
  PRINT RIGHT$(f$, 6)
NEXT
```
```
a.txt
c.txt
d.txt
ft/sub
```

### COPY ... AS

```
COPY source AS destination
```

Copies a file with `shutil.copy2`, which keeps timestamps. Both names are expressions, and `~` is expanded. A missing source sets `ERR` = 2; other failures set `ERR` = 1. Both are runtime errors, so trap them with `ON ERROR GOTO` if needed.

`COPY` is also a SQL keyword (DuckDB `COPY table TO 'file'`). A line is treated as the file-copy statement when it contains `AS` and no `TO` or `FROM`; otherwise it is sent to the database as SQL.

```basic
COPY "src.txt" AS "dst.txt"
PRINT "copied:"; FILE_EXISTS("dst.txt")
s$ = "src.txt"
COPY s$ AS "dst2.txt"
PRINT FILESIZE("dst2.txt")
DATABASE ENGINE DUCKDB
CREATE TABLE t AS SELECT 1 AS a;
COPY t TO 'out.csv' (HEADER);
PRINT FILE_EXISTS("out.csv")
```

```
copied:-1
 3
-1
```

### NAME ... AS

```
NAME oldname AS newname
```

Renames or moves a file or directory (`os.rename`). `~` is **not** expanded.

| Condition | ERR | Effect |
|---|---|---|
| Source missing | 2 | Error is raised |
| Target exists (where the OS reports it) | 17 | Error is raised |
| Any other failure | 1 | Error is raised |

On POSIX systems an existing target file is silently replaced.

### KILL

```
KILL filename
```

Deletes one file (`os.remove`). There is no wildcard support.

* If the file is missing, `KILL` sets `ERR` = 2 and `ERRMSG$`. What happens next depends on whether an `ON ERROR GOTO` handler is active:
  * **No handler:** `KILL` continues quietly, so cleanup code can delete files that may not exist.
  * **Handler active:** it raises `File not found: name`, so the handler runs (with `ERR` = 2) and can `RESUME NEXT`. Inside the handler itself `KILL` stays quiet, because errors there are not trapped again.

  ```basic
  ON ERROR GOTO trap
  KILL "missing.tmp"
  PRINT "after KILL"
  END
  trap:
  PRINT "handler: ERR ="; ERR
  RESUME NEXT
  ```
  ```
  handler: ERR = 2
  after KILL
  ```
* Other failures, such as trying to delete a directory, set `ERR` = 1 and raise.
* `KILL` with no argument is an error.

### MKDIR

```
MKDIR path
```

Creates a directory, including any missing parent directories (`os.makedirs(..., exist_ok=True)`). If the directory already exists, MKDIR does nothing and `ERR` stays 0. Failures set `ERR` = 1 and raise.

### CHDIR

```
CHDIR path
```

Changes the current working directory. A missing directory sets `ERR` = 2, a path that is not a directory sets 20, and any other failure sets 1. All of them raise. Read the current directory with `CURDIR$` (Chapter 3).

### RMDIR

```
RMDIR path
```

Removes an **empty** directory. A missing directory sets `ERR` = 2. Any other OS error, including "directory not empty", sets `ERR` = 39. Both raise.

```basic
MKDIR "work/a/b"
NAME "work/a.copy" AS "work/renamed.txt"
KILL "work/renamed.txt"
KILL "work/renamed.txt"
PRINT "KILL missing ERR="; ERR; " "; ERRMSG$
RMDIR "work/a/b"
ON ERROR GOTO h
RMDIR "work"
END
h:
PRINT "handler ERR="; ERR; " "; ERRMSG$
```
```
KILL missing ERR= 2 [Errno 2] No such file or directory: 'work/renamed.txt'
handler ERR= 39 [Errno 66] Directory not empty: 'work'
```

### Error codes set by file statements

| ERR | Meaning | Set by |
|---|---|---|
| 0 | Success | all |
| 1 | General error | OPEN, READ FILE, COPY, NAME, MKDIR, CHDIR, RMDIR, KILL, ZIP, UNZIP |
| 2 | File / directory not found | OPEN, READ FILE, COPY, NAME, CHDIR, RMDIR, KILL |
| 17 | Target already exists | NAME |
| 20 | Not a directory | CHDIR |
| 39 | Directory not empty or other OS error | RMDIR |

---

## 6.3 Archives and hash unpacking

### ZIP

```
ZIP archive$ FROM file_or_pattern$ [, file_or_pattern$ ...]
```

Behaviour:

* Each item that contains `*` or `?` is expanded with `glob`. Other items are added if they exist.
* Missing items print `Warning: ...` and are skipped.
* Entries are stored under their **base name** only, so the directory structure is flattened, using DEFLATE compression.
* Each file added prints `Added: path -> name`. The statement finishes with `Created <archive> with N files`.

* If no files are found, `ERR` = 1 and `ERRMSG$` = `No files found to zip`, and no archive is created. This is fatal when `SQL_FATAL_ERRORS` is ON, which is the default.

```basic
ZIP "out.zip" FROM "a.txt", "*.bas"
PRINT "ERR="; ERR
UNZIP "out.zip" TO "x"
```

```
Added: a.txt -> a.txt
Added: b.bas -> b.bas
Added: z.bas -> z.bas
Created out.zip with 3 files
ERR= 0
Extracted 3 files from out.zip
  -> x/a.txt
  -> x/b.bas
  -> x/z.bas
```

Only the `FROM` form is accepted. Older forms such as `ZIP "a.zip", "f1", "f2"` and `ZIP "a.zip" FILES "dir/*"` fail; `tests/zip.bas` has been updated to use `FROM`.

### UNZIP

```
UNZIP archive$ [TO target_dir$]
```

Extracts every entry of a ZIP archive into `target_dir$`, or into the current directory if no target is given. The target directory is created if it does not exist. The statement prints a summary and one line per entry, and sets `ERR` = 0 on success.

| Failure | Result |
|---|---|
| Archive missing | `ERR` = 2, `ERRMSG$` = `Archive not found: ...` |
| Not a ZIP file | `ERR` = 1, `ERRMSG$` = `Invalid ZIP file: ...` |
| Other error | `ERR` = 1, `ERRMSG$` = the message |

If `SQL_FATAL_ERRORS` is ON (the default), each failure also raises a runtime error. Use `SET SQL_FATAL_ERRORS OFF` to handle failures through `ERR` instead.

```basic
UNZIP "z.zip" TO "out1"
PRINT "UNZIP ERR="; ERR
SET SQL_FATAL_ERRORS OFF
UNZIP "bad.zip" TO "out1"
PRINT "bad ERR="; ERR; " "; ERRMSG$
```
```
Extracted 5 files from z.zip
  -> out1/a.txt
  -> out1/sub/
  -> out1/sub/deep/
  -> out1/sub/deep/d.txt
  -> out1/sub/c.txt
UNZIP ERR= 0
bad ERR= 1 Invalid ZIP file: File is not a zip file
```

The keyword is `TO`. `INTO`, which appears in the function's docstring, is rejected.

### UNPACK

```
UNPACK hash
```

Turns each key of a hash into a stand-alone variable:

* String values go into `key$` and other values into `key`. Any existing `$` on the key is removed first.
* `None`/null values become `""`.
* Keys that are not valid identifiers, such as `"bad key"`, are skipped.
* The argument must evaluate to a hash. Otherwise the error is `UNPACK statement requires a HASH variable.`

UNPACK is handy after `BROWSE ... INTO row` (`UNPACK row`) or after parsing JSON.

```basic
DIM h AS HASH
h("name") = "Ann"
h("age") = 42
h("bad key") = 1
UNPACK h
PRINT name$; " "; age
```
```
Ann  42
```

---

## 6.4 System and console

### SHELL

```
SHELL command$ [INTO out$]
```

Runs `command$` through the operating-system shell (`subprocess.run(..., shell=True)`).

* **Without `INTO`**, the command's standard output and standard error go straight to the terminal. They are not captured, and `SET OUTPUT` does not redirect them.
* **With `INTO out$`**, standard output is captured as text (UTF-8, with invalid bytes replaced) into `out$`. If the command wrote anything to standard error, that text goes into `ERRMSG$`. The destination must be a string variable.
* `ERR` is set to the command's exit code. If the process could not be started, `ERR` = -1 and an error is raised.
* Commands are OS-specific. `dir` and `type`, as used in some of the examples, exist only on Windows.

```basic
SHELL "echo hello from shell"
PRINT "ERR="; ERR
SHELL "echo captured; echo oops 1>&2; exit 3" INTO out$
PRINT "out$=["; out$; "] ERR="; ERR; " ERRMSG$=["; ERRMSG$; "]"
```
```
hello from shell
ERR= 0
out$=[captured
] ERR= 3 ERRMSG$=[oops
]
```

### BROWSER

```
BROWSER url$ [OPTIONS "new=1" | "new=2"]
```

Opens `url$` in the system default web browser (Python `webbrowser.open`). The URL can be a `file:///` path.

* `OPTIONS "new=1"` asks for a new window and `"new=2"` asks for a new tab. The default (0) reuses the current window.
* If no browser can be launched, `ERR` = 52 and `ERRMSG$` = `Could not open a web browser. Check system configuration.` An exception sets `ERR` = 1. Neither case stops the program.
* A non-string argument is a runtime error.

```basic
LET full_path$ = "file:///" + CURDIR$() + "/" + report_file$
BROWSER full_path$                     ' from examples/browser.bas
```

### BELL

```
BELL
```

Writes the ASCII BEL character (`\a`) to standard output with no newline, and flushes it. Whether this makes a sound depends on the terminal.

### INPUT

```
INPUT ["prompt" {; | ,}] var
```

Reads one line from standard input.

* The prompt must be a **string literal** followed by a semicolon or a comma. If there is no prompt, a single space is shown. No `?` is added.
* If `var` ends in `$` the text is stored as-is. Otherwise it must be a number: other input prints `?Redo from start` and asks again, as in classic BASIC.
* Only one variable per statement is supported.

```basic
INPUT "Name? "; n$
INPUT "Age? "; a
PRINT n$; a * 2
```
Given the input `Bob` and `21`:
```
Name? Age? Bob 42
```


---

## 6.5 HTTP: FETCH

```
FETCH url$
      [POST body | PUT body | PATCH body | DELETE [body]]
      [USING HEADERS req_hash]
      [USING FILE field$ = path$]
      { INTO var$ | TO FILE path$ }
      [HEADERS INTO resp_hash]
```

`FETCH` sends an HTTP request with the Python `requests` library. The clauses between the URL and the destination can appear in any order.

| Clause | Meaning |
|---|---|
| *(no method)* | `GET`. |
| `POST body` / `PUT body` / `PATCH body` | Send the hash variable `body` as the request body, **form-encoded** (`application/x-www-form-urlencoded`). The body is required for these three methods. Write the hash name on its own (`Payload`) or with empty parentheses (`Payload()`). |
| `DELETE [body]` | Send a DELETE request. The body is optional. |
| `USING HEADERS h` | Use the hash `h` as request headers. |
| `USING FILE field$ = path$` | Multipart upload of the local file `path$` under form field `field$`. Any POST/PUT/PATCH body is sent as extra form fields. The upload is ignored for GET and DELETE. |
| `INTO var$` | Store the response body, decoded as UTF-8, in `var$`. If the body is not valid UTF-8, the variable gets the literal text `Binary data received`. |
| `TO FILE path$` | Stream the response body to `path$`, writing it in binary mode in 8 KB chunks. |
| `HEADERS INTO h` | Must come after the destination. Stores the response headers in a hash, with key case exactly as the server sent it. |

Timeouts are 15 seconds, or 30 seconds when a file is uploaded. They cannot be configured.

**Result in `ERR`:**

| Situation | `INTO var$` | `TO FILE path$` |
|---|---|---|
| Any HTTP response | `ERR` = status code (200, 404, ...). The body is stored even for error statuses. | 2xx: `ERR` = status code and the file is written. 4xx/5xx: `ERR` = **-1** and the file is not created (`raise_for_status`). |
| Network error, timeout or bad host | `ERR` = -1 | `ERR` = -1 |
| Upload file not found | `ERR` = -2 | `ERR` = -2 |

`ERRMSG$` is not set by FETCH, and FETCH never raises an error for HTTP or network failures. Always test `ERR`. Note that a successful request leaves `ERR` = 200, **not 0**.

Notes:

* Hash values are sent in their string form, so the number `42` is sent as `"42.0"`. Convert numbers explicitly (for example `STR$` or `FORMAT$`, Chapter 3) if the server needs integers.
* Header keys keep the server's case. Many servers, including HTTP/2 servers, send lowercase names, so `h("Content-Type")` returns `0` while `h("content-type")` works. Under `SET HASH_KEYS IGNORE_CASE` lookups are upper-cased, but the stored keys are not, so lookups fail. Inspect the hash with `PRINT h` first.
* To parse a JSON response, use `PARSEJSON` (Chapter 3).

Example (run against httpbin.org; part of the output omitted):

```basic
FETCH "https://httpbin.org/get?x=1" INTO r$ HEADERS INTO h
PRINT "GET ERR="; ERR; "  "; h("content-type")

DIM payload AS HASH
payload("name") = "Ann"
payload("age") = 42
DIM hdr AS HASH
hdr("X-Test") = "abc"
FETCH "https://httpbin.org/post" POST payload USING HEADERS hdr INTO r$
j = PARSEJSON(r$)
PRINT "POST ERR="; ERR
PRINT j("form")
PRINT j("headers")("X-Test")

FETCH "https://httpbin.org/put" PUT payload() INTO r$
FETCH "https://httpbin.org/delete" DELETE INTO r$
FETCH "https://httpbin.org/post" POST payload USING FILE "file" = "up.txt" INTO r$
PRINT "UPLOAD ERR="; ERR; " "; PARSEJSON(r$)("files")

FETCH "https://httpbin.org/status/404" INTO r$
PRINT "404 INTO ERR="; ERR
FETCH "https://httpbin.org/status/404" TO FILE "x.out"
PRINT "404 TO FILE ERR="; ERR
FETCH "https://httpbin.org/image/png" TO FILE "img.png" HEADERS INTO h2
PRINT "TO FILE ERR="; ERR; " size="; FILESIZE("img.png")
FETCH "https://no-such-host.invalid/" INTO r$
PRINT "bad host ERR="; ERR
FETCH "https://httpbin.org/post" POST payload USING FILE "file" = "missing.txt" INTO r$
PRINT "missing upload ERR="; ERR
```
```
GET ERR= 200  application/json
POST ERR= 200
{
  "age": "42.0",
  "name": "Ann"
}
abc
UPLOAD ERR= 200 {
  "file": "hello upload\n"
}
404 INTO ERR= 404
404 TO FILE ERR=-1
TO FILE ERR= 200 size= 8090
bad host ERR=-1
missing upload ERR=-2
```

`examples/convertcsv.io.fetch.bas` (multipart upload with headers) and `examples/npilinks.bas` (`FETCH url$ TO FILE local_file$`) show real-world use.

---

## 6.6 E-mail: SET EMAIL and EMAIL

### SET EMAIL

```
SET EMAIL keyword value [keyword value ...]
```

Sets the e-mail configuration. Each value is an expression. Settings **accumulate** across `SET EMAIL` statements: a later statement adds to or replaces individual keys and never clears the others. Each `SET EMAIL` prints `Email provider configured.` to standard error.

| Keyword | Used by | Notes |
|---|---|---|
| `PROVIDER` | all | `"SMTP"`, `"SENDGRID"` or `"MAILGUN"` (case-insensitive). The value is checked only when `EMAIL` runs. |
| `SENDER` | all | The From address. |
| `APIKEY` | SendGrid, Mailgun | |
| `DOMAIN` | Mailgun | The sending domain, used in `https://api.mailgun.net/v3/<domain>/messages`. |
| `HOST` | SMTP | |
| `PORT` | SMTP | Converted to an integer. |
| `USER`, `PASSWORD` | SMTP | Login credentials. SMTP always logs in. |
| `SECURITY` | SMTP | `"SSL"` uses `SMTP_SSL` (typically port 465). `"TLS"` uses plain SMTP followed by `STARTTLS` (typically 587). Anything else, or omitting it, uses an unencrypted connection. |

Required keys are checked when `EMAIL` runs:

* SendGrid: `APIKEY`, `SENDER`
* Mailgun: `APIKEY`, `SENDER`, `DOMAIN`
* SMTP: `HOST`, `PORT`, `USER`, `PASSWORD`, `SENDER`

A missing key or an unsupported provider is a runtime error.

```basic
SET EMAIL PROVIDER "SMTP" HOST "smtp.example.com" PORT 587 _
          USER "me@example.com" PASSWORD pw$ SENDER "me@example.com" SECURITY "TLS"

SET EMAIL PROVIDER "SENDGRID" APIKEY ENVIRON$("SENDGRID_KEY") SENDER "noreply@example.com"

SET EMAIL PROVIDER "MAILGUN" APIKEY key$ DOMAIN "mg.example.com" SENDER "app@mg.example.com"
```

### EMAIL

```
EMAIL [TO to$] [CC cc$] [BCC bcc$] [SUBJECT subject$] [BODY text$] [HTMLBODY html$] [ATTACH files$]
```

Sends one message through the configured provider. The clauses can appear in any order and the statement ends at the end of the line (or a `:`).

* `TO`, `CC`, `BCC` and `ATTACH` take **comma-separated lists in a single string**.
* `SUBJECT` defaults to `(No Subject)`.
* `BODY` is the plain-text part and `HTMLBODY` is the HTML part. You can supply both.
* Attachments are given as file paths. Each file is attached under its base name.
* `EMAIL` without a prior `SET EMAIL PROVIDER` is a runtime error.

How each provider sends the message:

| Provider | Mechanism |
|---|---|
| SendGrid | JSON POST to `https://api.sendgrid.com/v3/mail/send` with a Bearer token. Attachments are base64-encoded. |
| Mailgun | Form POST with basic authentication (`api`, key). Attachments are sent as multipart `attachment` fields. |
| SMTP | A `MIMEMultipart` message. BCC addresses are added to the envelope recipients only, never to the headers. |

**Result:** `ERR` = 0 on success. For SendGrid and Mailgun, a non-2xx response sets `ERR` to the HTTP status and `ERRMSG$` to the response text. Any exception sets `ERR` = -1 and `ERRMSG$` to the message without stopping the program. This includes SMTP connection, login and send failures, and a missing attachment file. SMTP has no HTTP status, so a message that the server accepted simply leaves `ERR` = 0.

```basic
SET EMAIL PROVIDER "SMTP" HOST "smtp.example.com" PORT 587 USER u$ PASSWORD p$ _
          SENDER "reports@example.com" SECURITY "TLS"
EMAIL TO "alice@example.com, bob@example.com" CC "mgr@example.com" _
      SUBJECT "Monthly report" BODY "See attached." _
      HTMLBODY "<p>See <b>attached</b>.</p>" ATTACH "report.pdf, data.csv"
IF ERR <> 0 THEN PRINT "Send failed: "; ERRMSG$
```

The following was tested without sending anything, against a closed local port:

```basic
SET EMAIL PROVIDER "SMTP" HOST "127.0.0.1" PORT 1 USER "u" PASSWORD "p" SENDER "me@example.com" SECURITY "tls"
EMAIL TO "a@example.com" SUBJECT "x" BODY "y" ATTACH "missing.pdf"
PRINT "ERR="; ERR; " MSG="; LEFT$(ERRMSG$, 45)
EMAIL TO "a@example.com" SUBJECT "x" BODY "y"
PRINT "ERR="; ERR; " MSG="; ERRMSG$
```
```
Email provider configured.
ERR=-1 MSG=Attachment file not found: missing.pdf at lin
ERR=-1 MSG=[Errno 61] Connection refused
```

---

## 6.7 Text screens

DbBasic can draw full-screen, 1990s-style text applications: a coloured screen, boxes, `@ ... SAY ... GET` entry fields edited with `READ`, light-bar menus and a scrolling grid for query results. `examples/retro_contacts.bas` is a complete contact manager built this way.

The screen is drawn with ANSI escape sequences, so `PRINT` keeps working between screen statements and no extra packages are needed. The code is in `src/dbscreen.py`. It has been tested in macOS terminals; Linux terminals work the same way. Windows 10 and later (Windows Terminal or the console) are supported by the code, but the Windows key handling has not been tested yet.

**Coordinates** are `row, col`, counted from 1 at the top left, as with `LOCATE`.

```basic
COLOR 15, 1                          REM bright white on blue
CLS
BOX 2, 5, 9, 60, "Customer" DOUBLE
name$ = "" : phone$ = "" : credit = 0
@ 4, 8 SAY "Name  : " GET name$  PICTURE "@!S20"
@ 5, 8 SAY "Phone : " GET phone$ PICTURE "(999) 999-9999"
@ 6, 8 SAY "Credit: " GET credit VALID credit >= 0
READ
IF LASTKEY$ = CHR$(27) THEN GOTO cancelled
```

```
    ╔══════════════════════ Customer ══════════════════════╗
    ║                                                      ║
    ║  Name  : ANN SMITH                                   ║
    ║  Phone : (555) 123-4567                              ║
    ║  Credit: 12                                          ║
    ║                                                      ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
```

### CLS, LOCATE, COLOR and BOX

| Statement | Effect |
|---|---|
| `CLS` | Clears the screen in the current colours and moves the cursor to 1, 1. Pending `GET` fields are discarded. |
| `LOCATE row [, col]` | Moves the cursor. The next `PRINT` or `INPUT` starts there. `col` defaults to 1. |
| `COLOR [fg] [, bg] [, field_fg] [, field_bg]` | Sets the text colours. Any value can be left out (`COLOR , 4` changes only the background). `field_fg`/`field_bg` colour `GET` fields, the menu bar and the `BROWSE` bar; they start as black on white. |
| `BOX top, left, bottom, right [, title$] [DOUBLE]` | Draws a single- or double-line box, clears its inside in the current colours, and centres the title in the top line. |

The colour numbers are those of QBasic:

| | | | | | | | |
|---|---|---|---|---|---|---|---|
| 0 black | 1 blue | 2 green | 3 cyan | 4 red | 5 magenta | 6 brown | 7 white |
| 8 grey | 9 light blue | 10 light green | 11 light cyan | 12 light red | 13 light magenta | 14 yellow | 15 bright white |

### @ ... SAY ... GET

```
@ row, col [SAY expr [PICTURE mask$]] [GET target [PICTURE mask$] [VALID condition] [MESSAGE text$]
                                                  [WHEN condition] [LOOKUP (SELECT ...)]]
```

The `GET` clauses can come in any order.

`SAY` writes the value of `expr` at the position. With `PICTURE`, the value is formatted as `FORMAT$(expr, mask$)` would format it: `@ 20, 1 SAY 1234.5 PICTURE "#,###.##"` shows `1,234.50`.

`GET` puts an entry field for a variable straight after the `SAY` text, or at `col` if there is no `SAY`. It shows the current value in the field colours. Nothing is edited until `READ`.

The target can be a variable (`name$`, `qty`), a hash field (`rec.name`, `rec.ship.city`, `h("key")`) or an array element (`a(2)`). A hash field is found the way `rec.name` reads it, ignoring case, so `GET rec.name` edits the `NAME` column of a row from `FOR rec IN (SELECT ...)` or `BROWSE ... INTO rec`. A field that does not exist yet is created when `READ` stores it. A target whose name ends in `$`, or that holds a string, gets a text field; one that holds a number gets a numeric field. A whole array or hash can't be edited.

Editing a record hash keeps a form short, because bind variables can name hash fields too:

```basic
FOR rec IN (SELECT * FROM contacts WHERE id = :id)
    @ 5, 13 SAY "Last  : " GET rec.last_name PICTURE "@!S20"
    @ 6, 13 SAY "Email : " GET rec.email     PICTURE "@S40"
    READ
    IF LASTKEY$ <> CHR$(27) THEN UPDATE contacts SET last_name = :rec.last_name, email = :rec.email WHERE id = :id;
NEXT
```

| `GET` picture | Meaning |
|---|---|
| (none) | Text: as wide as the current value, and at least 20. Numbers: 10 wide. |
| `@!` | Upper-case every letter typed. |
| `@Sn` | A field `n` characters wide, for example `@S30`. Combine with `!`: `@!S30`. |
| template | One character per position. `9` digit, `A` letter, `N` letter or digit, `X` any character, `!` any character in upper case, `#` digit, space or sign. Any other character is fixed and is skipped by the cursor, as in `(999) 999-9999`. The stored value includes the fixed characters, or is `""` when nothing was typed. |

For a numeric field, a template only sets the width. The value is typed as a number (commas are ignored), and an entry that is not a number is refused with a beep.

`VALID condition` is checked whenever the cursor leaves the field, after the variable has been given the typed value. If the condition is false, DbBasic beeps and the cursor stays in the field. With `MESSAGE text$`, the text is also shown on the bottom line of the screen until the next key, so the user knows why:

```basic
@ 5, 5 SAY "Credit: " GET credit VALID credit <= 5000 MESSAGE "Limit is 5,000"
```

`WHEN condition` is checked when the cursor would move into the field. If it is false, the field is skipped, in whichever direction the cursor was moving. Use it for fields that only apply sometimes. A field skipped as the last one ends `READ`:

```basic
@ 3, 5 SAY "Type  : " GET type$ PICTURE "!" VALID type$ = "P" OR type$ = "B" MESSAGE "Type must be P or B"
@ 5, 5 SAY "Credit: " GET credit WHEN type$ = "B"
```

A condition ends at the end of the statement or at the next clause word (`MESSAGE`, `WHEN`, `LOOKUP`, `PICTURE`, `VALID`), so `VALID message$ <> ""` still works with a variable called `message$`.

**LOOKUP** gives a field a list of allowed values from a query. Its first column holds the values; any other columns are shown as a description:

```basic
@ 4, 5 SAY "State : " GET state$ PICTURE "!!" LOOKUP (SELECT code, name FROM states ORDER BY code)
```

- F2 opens the list under the field (above it if there is no room). Enter picks a row and puts its first column in the field; Esc closes the list.
- Leaving the field with a value that is not in the list (ignoring case and spaces) opens the list too, at the first row that starts with what was typed. Picking a row accepts it and moves on; Esc keeps the cursor in the field. An empty field is not checked; add `VALID state$ <> ""` to require a value.
- The query runs each time the list is needed, so bind variables (`:country$`) see the current values of other fields.

```
    State : ZZ
    Credit: ┌─────── Choose ───────┐
    Name  : │ code │ name          │
            │──────────────────────│
            │ CA   │ California    │
            │ FL   │ Florida       │
            │ NY   │ New York      │
            │ TX   │ Texas         │
            │ 1 of 4   Enter=select│
            └──────────────────────┘
```

### READ

`READ` edits the pending `GET` fields in the order they were defined, then clears the list.

| Key | Action |
|---|---|
| Enter, Tab, Down | Next field. On the last field, Enter, Tab or Down ends `READ`. |
| Shift-Tab, Up | Previous field. |
| PgDn, PgUp, Ctrl-W | End `READ`. |
| Esc | End `READ` and put back the values every field had when `READ` started. |
| Left, Right, Home, End | Move within the field. |
| Backspace, Del | Delete. |
| Ins | Switch between insert mode (the default) and overwrite mode. |
| Ctrl-Y | Clear the field. |
| F2 | Open the field's `LOOKUP` list. |

Each value is stored when you leave its field. The first key you type in a numeric field replaces the old number.

**Auto-advance.** `SET AUTOADVANCE ON` makes `READ` behave like Clipper with `SET CONFIRM OFF`: typing a character into a field's last position moves on as if Enter had been pressed. A field with a template such as `"99999"` or `"(999) 999-9999"` is then filled without pressing Tab, and filling the last field ends `READ` (`LASTKEY$` is `CHR$(13)`). `VALID` still applies: a refused value keeps the cursor in the field. `SET AUTOADVANCE OFF`, the default, keeps the cursor in a full field until Enter, Tab or an arrow key. Clipper's spelling also works, with the opposite sense: `SET CONFIRM OFF` is `SET AUTOADVANCE ON`, and `SET CONFIRM ON` is `SET AUTOADVANCE OFF`. The setting also applies to `EDIT RECORD`, but not to a cell being edited in `BROWSE`. Afterwards, `LASTKEY$` holds the key that ended `READ`, so `IF LASTKEY$ = CHR$(27)` tells you the user cancelled.

### ALERT()

```
choice = ALERT(message$ [, button1$, button2$, ...])
choice = ALERT(message$, buttons)               REM an array of labels
```

`ALERT` shows a centred, double-lined box with a message and a row of buttons, waits for a choice and puts the screen back. A `;` in the message starts a new line. Left/Right (or Tab) move between the buttons, Enter chooses, and the first letter of a button chooses it at once. It returns the button's number, counting from 1, or `0` for Esc. With no buttons there is a single `OK`.

```basic
IF ALERT("Save changes?;They can't be undone.", "Yes", "No", "Cancel") = 1 THEN GOSUB save
```

```
╔═════════════════════════╗
║      Save changes?      ║
║  They can't be undone.  ║
║                         ║
║   Yes    No    Cancel   ║
╚═════════════════════════╝
```

### MENUBAR$()

```
choice$ = MENUBAR$([row,] "Title:item|item|...", "Title:item|...", ...)
choice$ = MENUBAR$([row,] menus)                 REM an array of the same strings
```

`MENUBAR$` draws a menu bar across the screen, on row 1 unless `row` is given, with a pull-down menu under each title. Each argument is a title, a `:` and its items separated by `|`. An item `-` draws a separator line. A title with no items, such as `"Exit"`, is chosen directly.

```basic
DO
    choice$ = MENUBAR$("File:Open|Save|-|Quit", "Customers:Browse|Add|Report", "Help:About")
    IF choice$ = "Customers.Browse" THEN BROWSE "customers" EDIT
    IF choice$ = "Help.About" THEN x = ALERT("Contacts 1.0")
LOOP UNTIL choice$ = "File.Quit" OR choice$ = ""
```

```
 File   Customers   Help
       ┌────────┐
       │ Browse │
       │ Add    │
       │ Report │
       └────────┘
```

| Key | On the bar | In a pull-down |
|---|---|---|
| Left, Right | Move to the previous or next title. | Open the neighbouring menu. |
| Enter, Down | Open the menu (or choose a title with no items). | Enter chooses the item; Down moves down. |
| Up, Home, End | | Move; the separator is skipped. |
| A letter | Opens the title starting with it. | Chooses the item starting with it. |
| Esc | Return `""`. | Close the pull-down. |

It returns `"Title.Item"`, using the text as written, so the program reads naturally and does not depend on the order of the items. A title chosen directly gives `"Title"`. The bar stays on the screen as part of the program's display. The pull-downs are removed, and what they covered is put back, along with the cursor.

### MENU()

```
choice = MENU(row, col, item1$, item2$, ...)
choice = MENU(row, col, items)                 REM an array of items
```

`MENU` draws a box at `row, col` with one item per line and a highlighted bar. Up and Down move the bar, Enter chooses, and typing the first letter of an item chooses it at once. It returns the item number, counting from 1, or `0` for Esc. When it returns, the menu disappears and what it covered is put back.

### BROWSE

```
BROWSE (SELECT ...) | BROWSE table$  [EDIT [KEY key$]] [AT top, left, bottom, right] [TITLE title$] [INTO var]
```

`BROWSE` runs the query and shows the rows in a box: a header line, the rows, and a status line (`2 of 3   Enter=select  Esc=cancel`). Without `AT`, it fills the terminal. A string that does not start with `SELECT` or `WITH` is taken as a table name. Bind variables (`:id`) work as in any query.

Up/Down, PgUp/PgDn and Home/End move the bar, and Left/Right scroll the columns. Columns are as wide as their widest value, up to 30 characters. Enter chooses the row. `INTO var` then receives it as a hash, keyed by upper-case column name and by column number, like the row of `FOR row IN (SELECT ...)`. Esc gives an empty hash. When `BROWSE` ends, what the grid covered is put back.

**Editing.** With `EDIT`, the grid is a spreadsheet-like editor for the table. Each change is saved at once: cell edits with an `UPDATE`, new rows with an `INSERT`, deleted rows with a `DELETE`:

| Key | Action |
|---|---|
| Left, Right, Tab, Shift-Tab | Move between cells. The current cell is shown in reverse. |
| Enter or F2 | Edit the current cell, starting from its value. |
| Any character | Edit the current cell, starting with that character (the old value is replaced). |
| Enter, Tab, Up, Down (while editing) | Save the cell. Tab, Up and Down also move. |
| Esc (while editing) | Cancel the edit. |
| Ins | Add a row. A blank form opens over the grid, the same form `EDIT RECORD` shows for a new row: one field per column, saved with an `INSERT` (see [EDIT RECORD](#edit-record) for how the key is filled in). The grid then reloads and moves to the new row. |
| Del | Delete the current row. The status line asks `Delete this row? (Y/N)`; only `Y` deletes it. |
| Esc | End `BROWSE`. `INTO` gets an empty hash. |

- `BROWSE "items" EDIT` edits a table by its `rowid`, which is fetched but not shown.
- A query needs the column that identifies a row: `BROWSE (SELECT id, name FROM items) EDIT KEY "id"`. The query must read `FROM` one table, and the edited columns must be plain column names of that table. The `KEY` column can't be edited.
- A cell that held a number is edited as a number. Emptying it stores `NULL`. An emptied text cell follows `SET NULL_HANDLING`: `NULL` by default.
- If the database refuses a change (a `CHECK` or `NOT NULL` constraint, a wrong type), DbBasic beeps, the status line shows `Not saved: ...` (or `Not deleted: ...`) with the database's message, and the cell keeps its old value. A refused new row keeps its form open, as in `EDIT RECORD`.

`examples/retro_contacts.bas` uses `BROWSE ... EDIT KEY "id"` for its contact list.

### EDIT RECORD

```
EDIT RECORD (SELECT ... FROM table WHERE ...) [KEY key$] [AT top, left] [TITLE title$] [INTO var]
```

`EDIT RECORD` is a whole entry form in one line, for when the layout doesn't matter. It runs the query and shows a box, centred unless `AT` is given, with one labelled field per column. The labels come from the column names (`last_name` becomes `Last Name`), and the title defaults to the table name.

```basic
EDIT RECORD (SELECT * FROM contacts WHERE id = :id) TITLE "Contact" INTO rec
```

```
┌──────────────── Contact ─────────────────┐
│                                          │
│        Id : 1                            │
│ Last Name : jones                        │
│     Email : a@x.com                      │
│    Credit : 50                           │
│                                          │
│ Enter=next  PgDn=save  Esc=cancel        │
└──────────────────────────────────────────┘
```

- **Keys:** the fields are edited as with `READ`. Enter on the last field, or PgDn, saves; Esc cancels and changes nothing.
- **Key column:** `KEY` names the column that identifies the row. It defaults to the table's primary key, and it is shown but can't be edited.
- **Saving an existing row:** an `UPDATE` of the columns that changed.
- **No matching row:** the form opens blank and saves with an `INSERT`. The key can be typed. Leave it at 0 to let SQLite number the row (`INTEGER PRIMARY KEY`). DuckDB has no automatic numbering unless the column has a `DEFAULT nextval(...)`, so type the key there.
- **Refused changes:** if the database refuses the change (a `CHECK` or `NOT NULL` constraint, a wrong type), DbBasic beeps and shows `Not saved: ...` under the box. After a key press, the form is shown again with what you typed, starting at the first field.
- **`INTO var`:** receives the saved record as a hash, keyed by upper-case column name, or an empty hash after Esc. After an `INSERT` on SQLite, it holds the new row's key.
- **Rules:** the query must read `FROM` one table and find at most one row, and its columns must be plain column names of that table. Numbers are edited as numbers, and an emptied text field follows `SET NULL_HANDLING`. What the form covered is put back when it closes.

Use `@ ... SAY ... GET` and `READ` when you want your own layout, pictures or `VALID` checks.

### EDIT TEXT

```
EDIT TEXT target [AT top, left, bottom, right] [TITLE title$]
```

`EDIT TEXT` is a memo editor: a box in which a multi-line string can be edited, like Clipper's MEMOEDIT. The target can be anything `GET` accepts: a variable (`notes$`), a hash field (`rec.notes`) or an array element. Lines are separated by `CHR$(10)`. Without `AT`, the box fills the screen with a small margin.

```basic
EDIT TEXT rec.notes AT 3, 5, 12, 50 TITLE "Notes"
IF LASTKEY$ <> CHR$(27) THEN UPDATE customers SET notes = :rec.notes WHERE id = :rec.id;
```

```
┌────────────────── Notes ───────────────────┐
│first line ok                               │
│third                                       │
│second line                                 │
│                                            │
└─ Ln 2, Col 6  Ctrl-W=save  Esc=cancel ─────┘
```

| Key | Action |
|---|---|
| Arrows, Home, End, PgUp, PgDn | Move. Left and Right wrap to the previous or next line. |
| Enter | Split the line at the cursor. |
| Backspace, Del | Delete a character; at the start or end of a line, join it to the line before or after. |
| Tab | Insert spaces up to the next multiple of 4. |
| Ctrl-Y | Delete the current line. |
| Ins | Switch between insert mode (the default) and overwrite mode. |
| Ctrl-W or F10 | Save: the target gets the text, and `LASTKEY$` is `CHR$(23)` or `F10`. |
| Esc | Cancel. If anything was changed, `ALERT` asks `Discard your changes?` first. The target keeps its old value, and `LASTKEY$` is `CHR$(27)`. |

Lines are not wrapped: a line longer than the box scrolls sideways while you edit it, so the saved text has exactly the lines you typed. The line and column are shown in the bottom border, and the screen under the box is put back afterwards.

### VIEW

```
VIEW FILE path$      [AT top, left, bottom, right] [TITLE title$]
VIEW (SELECT ...)    [AT ...] [TITLE title$]
VIEW text$           [AT ...] [TITLE title$]
```

`VIEW` shows text in a read-only, scrolling box: a file, the result of a query (laid out as the text table a `SELECT` prints, with box-drawing lines), or any string. Without `AT`, it fills the screen. A file's name is the default title; tabs are expanded to 8 columns.

```basic
VIEW FILE "report.txt" AT 2, 2, 12, 60
VIEW (SELECT region, SUM(amount) AS total FROM sales GROUP BY region) TITLE "Sales"
```

```
┌───────────────────────── report.txt ────────────────────┐
│Line 057 of the report  TOTAL                            │
│Line 058 of the report                                   │
│...                                                      │
└─ 57-65 of 100  /=find  n=next  Esc=close ───────────────┘
```

| Key | Action |
|---|---|
| Up, Down, Enter | Scroll a line. |
| PgUp, PgDn, Space | Scroll a page. |
| Home, End | Go to the start or the end. |
| Left, Right | Scroll sideways, 8 columns at a time. |
| `/` or Ctrl-F | Search: type the text on the status line and press Enter. The search ignores case and starts at the top line shown; the line found is highlighted. |
| `n` or F3 | Find the next match, wrapping round to the start. `Not found: ...` is shown when there is none. |
| Esc or `q` | Close the viewer. `LASTKEY$` holds the key. |

A missing file is an error with `ERR = 2`. What the box covered is put back when it closes. A variable called `file` can still be viewed: `VIEW file` and `VIEW file AT ...` show its value.

### SAVESCREEN and RESTSCREEN

```
saved$ = SAVESCREEN()                          REM the whole screen
saved$ = SAVESCREEN(top, left, bottom, right)  REM an area
RESTSCREEN saved$
```

`SAVESCREEN` copies the screen, or an area of it, with its colours and the cursor position, into a string. `RESTSCREEN` puts that area back where it came from and returns the cursor. Use them around a pop-up window:

```basic
saved$ = SAVESCREEN(8, 20, 14, 60)
BOX 8, 20, 14, 60, "Warning" DOUBLE
@ 11, 24 SAY "Credit limit exceeded. Press a key."
k$ = INKEY$(0)
RESTSCREEN saved$
```

A terminal cannot report what it is showing, so DbBasic keeps its own copy of the screen. The copy includes everything drawn by `CLS`, `BOX`, `SAY`, `GET`, `MENU` and `BROWSE`, and the text of `PRINT`, `PRINT USING` and `INPUT` once a screen statement has been used. Output that bypasses it, such as query result tables, `SHELL` output or error messages, is not in the copy, and `RESTSCREEN` will draw over it with what the copy holds. `CLS` resets the copy to the terminal's current size.

Compare two saved strings to see whether the screen changed: `IF SAVESCREEN() <> saved$ THEN ...`.

### INKEY$ and LASTKEY$

| Function | Returns |
|---|---|
| `INKEY$` | The key that has been pressed, or `""` if none is waiting. It does not wait. |
| `INKEY$(0)` | The next key, waiting as long as it takes. |
| `INKEY$(n)` | The next key, waiting at most `n` seconds; `""` if none arrives. |
| `LASTKEY$` | The key that ended the last `READ`, `MENU` or `BROWSE`, or the last key `INKEY$` returned. |

Ordinary keys come back as characters: Enter is `CHR$(13)`, Esc `CHR$(27)`, Tab `CHR$(9)` and Backspace `CHR$(8)`. Other keys come back as names: `UP`, `DOWN`, `LEFT`, `RIGHT`, `HOME`, `END`, `PGUP`, `PGDN`, `INS`, `DEL`, `BTAB` (Shift-Tab) and `F1` to `F12`.

```basic
PRINT "Press a key (Esc to stop)"
DO
    k$ = INKEY$(0)
    IF k$ = CHR$(27) THEN EXIT DO
    PRINT "You pressed "; k$
LOOP
```

### Keyboard and terminal

While a program reads keys, the terminal does not echo them and passes Ctrl-S, Ctrl-Q, Ctrl-Y, Ctrl-V and Ctrl-O to the program. Ctrl-C still stops the program. `INPUT` switches the terminal back to normal line editing. When the program ends, the colours, the cursor and the terminal mode are restored. The screen contents are left as they are, as they were in DOS.

When standard input is not a terminal, keys are read from it as a stream, with arrow keys written as their escape sequences (`\x1b[A` for Up). This is how `tests/screen.bas` and `examples/retro_contacts.bas` are run by the test runner.

---

## 6.8 TUI forms (archived)

The declarative forms (`FORM ... ENDFORM`, `OPENFORM`, `GRIDEDIT`), built on the Textual library in `src/tui_runner.py`, have been removed from `main`. The text-screen statements in [6.7](#67-text-screens) replace them with less code:

| Old | New |
|---|---|
| `GRIDEDIT "orders"` | `BROWSE "orders" EDIT` (Enter edits a cell, Ins adds a row, Del deletes one) |
| A list `FORM` with `OPENFORM` and `FORM_SELECTED_ID` | `BROWSE (SELECT ...) INTO row` |
| An entry `FORM`, `FORM_RESULT$`, `FORM_DATA` and an `UPDATE` | `@ ... SAY ... GET`, `READ`, `LASTKEY$` and an `UPDATE` |
| `BUTTON` actions | `MENU(...)` |

`textual` is no longer a dependency. The last version with forms, including the form examples, is kept on the `archive/forms` branch.

---

## 6.9 Implementation notes / discrepancies

These were found while checking the source against behaviour. Line numbers refer to `src/dbbasic.py` unless stated otherwise.

1. **`COPY ... AS`** (fixed): the dispatcher looked for an identifier, but the lexer emits a `COPY` token, so the statement never ran.
2. **`ZIP`** (fixed): the `FROM` check compared the wrong token and could never pass. It also created an empty archive and reset `ERR` to 0 when no files matched.
3. **`UNZIP`** (fixed). For a missing archive, `ERR` was set to 2 and then overwritten with 1; it now stays 2. The archive name expands `~`. UNZIP errors are still fatal unless `SET SQL_FATAL_ERRORS OFF`, which ties archive handling to a SQL setting.
4. **`PRINT #n, USING ...`** (fixed). Without a trailing `;` it failed with `cannot access local variable 'parts'`, and with one no line ending was written.
5. **`OPEN` / `READ FILE` errors** (fixed). The generic error path set `ERRMSG$` to a tuple and left `ERR` at 0, and `OPEN` printed `DEBUG OPEN EXCEPTION`. Both now set `ERR` = 1 and `ERRMSG$` to the message, and expand `~`.
6. **`WRITE #n` line endings** (fixed). They were `\r\n` on all platforms while `PRINT #n` used `os.linesep`; both now use `os.linesep`. `WITH OPTIONS` values are passed to `csv.writer` as strings, so non-string dialect options (for example `quoting=1`) fail.
7. **`INPUT`** (fixed). `HELP INPUT` showed a comma after the prompt but only `;` was accepted, and non-numeric input to a numeric variable was a fatal error. Both separators work now, and bad numeric input asks again. Only a literal prompt and a single variable are supported.
8. **`LINE INPUT #` and `PRINT #` on a closed handle** (fixed). They raised a bare `KeyError` (`Runtime Error: 5`); the error is now `File #5 is not open.`. `LINE INPUT` past EOF still returns `""`; test `EOF(n)` first.
9. **`~` in file names** (fixed). `NAME`, `OPEN`, `READ FILE` and `UNZIP` now expand `~`, like `KILL`, `MKDIR`, `CHDIR`, `RMDIR`, `FILES` and `COPY`.
10. **`FILES RECURSIVE`** includes every directory whatever the pattern (unless `WITH FILESONLY`), while `FOR ... IN FILES(... RECURSIVE)` filters directories by the pattern. Arrays filled by `FILES ... INTO` start at index 0, like every other array.
11. **Multi-word keywords inside strings** (fixed). The lexer used to collapse `WITH DETAILS`, `TO FILE`, `READ FILE` and similar pairs even inside string literals, so `PRINT "TO FILE"` printed `TOFILE`. Strings and comments are now left unchanged.
12. **FETCH.**
    * `ERR` is 200 on success, not 0.
    * HTTP error statuses are reported differently for `INTO` (the status code) and `TO FILE` (-1).
    * `ERRMSG$` is never set.
    * Response header keys are stored without hash-key normalisation, so `SET HASH_KEYS IGNORE_CASE` makes them unreachable.
    * Numeric body values are sent as `"42.0"`.
    * `GET` cannot send a body.
13. **EMAIL.**
    * Errors raised during sending (missing attachment, SMTP failures) are caught and turned into `ERR` = -1, but configuration errors are fatal.
    * `HELP EMAIL` (fixed) listed only TO/SUBJECT/BODY/ATTACH; it now shows CC, BCC and HTMLBODY too.
    * `SET EMAIL` settings never reset between providers.
    * For SMTP, a missing `TO` is not checked.
14. **Forms** (archived). `FORM`, `OPENFORM` and `GRIDEDIT` have been moved to the `archive/forms` branch (see 6.8). Their open issues there were: `PLACEHOLDER` not displayed, debug output on every button press, field `TYPE NUMBER` doing no conversion, `MATCHES` not working with a `CHOICE`, non-numeric primary keys failing in `FORM_SELECTED_ID`, unescaped `WHERE`/`ORDER BY` text and no delete confirmation in `GRIDEDIT`.
15. *(merged into item 14)*
16. *(merged into item 14)*
17. **Web runner** (removed). The experimental web runner (`src/dbbasicweb.py`, `.htb` templates, the `REDIRECT` statement, `Interpreter.execute()` and the unused `WebFormRunner` import) has been removed from `main`. Its known problems were the `cgi` dependency (removed in Python 3.13), one interpreter shared by all requests, an unsanitised request path, and no static files. The last working version is kept on the `experiment/web-runner` branch.
18. **`SHELL` without `INTO`** writes directly to the process's stdout, bypassing `SET OUTPUT`.
19. **Text screens are a prototype** (6.7, new). Known limits:
    - `SAVESCREEN` and `RESTSCREEN` (added) work from DbBasic's own copy of the screen, which does not include query tables, `SHELL` output or error messages;
    - (added) `GET` edits hash fields and array elements as well as variables;
    - a numeric field's `PICTURE` sets only its width;
    - `BROWSE` reads every row into memory (and again after a row is added);
    - the Windows key handling has not been tested;
    - (fixed) words such as `choice` and `title`, once reserved by the FORM statements, are ordinary variable names again.
