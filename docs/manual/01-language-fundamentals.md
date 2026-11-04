# Chapter 1: Language Fundamentals

This chapter describes the core of the DbBasic language: how a source file is
read and prepared, how it is split into tokens, what kinds of values exist,
how variables, arrays and hashes work, and how expressions are evaluated.
Everything here comes from the interpreter source (`src/dbbasic.py`). Every
example was run against that interpreter, and the output shown is the real
output.

Other chapters cover the rest of the language:

- Chapter 2: Control Flow, Procedures & Program Control
- Chapter 3: Built-in Functions
- Chapter 4: Database, SQL & Output
- Chapter 5: Data Loading, Conversion & Analysis
- Chapter 6: Files, System, Network & User Interface

## Contents

1. [Running a program](#11-running-a-program)
2. [Program structure and source format](#12-program-structure-and-source-format)
3. [Comments](#13-comments)
4. [Source preprocessing](#14-source-preprocessing)
   - [INCLUDE](#141-include)
   - [Line continuation](#142-line-continuation)
   - [ECHO](#143-echo)
5. [The lexer](#15-the-lexer)
   - [Keywords and reserved words](#151-keywords-and-reserved-words)
   - [Identifiers and the `$` sigil](#152-identifiers-and-the--sigil)
   - [Numeric literals](#153-numeric-literals)
   - [String literals](#154-string-literals)
   - [Backtick strings and `${expr}` interpolation](#155-backtick-strings-and-expr-interpolation)
   - [Embedded SQL in the token stream](#156-embedded-sql-in-the-token-stream)
6. [Data types](#16-data-types)
7. [Variables and scope](#17-variables-and-scope)
8. [Assignment: LET](#18-assignment-let)
9. [Declarations: DIM and REDIM](#19-declarations-dim-and-redim)
10. [Arrays](#110-arrays)
11. [Hashes](#111-hashes)
12. [Array statements](#112-array-statements)
13. [FOR EACH over a hash](#113-for-each-over-a-hash)
14. [Operators and precedence](#114-operators-and-precedence)
15. [Expressions and truth values](#115-expressions-and-truth-values)
16. [Case sensitivity summary](#116-case-sensitivity-summary)
17. [Implementation notes / discrepancies](#117-implementation-notes--discrepancies)

---

## 1.1 Running a program

```
python src/dbbasic.py program.bas [arg1 arg2 ...]
python src/dbbasic.py - [args]          # read program from standard input
python src/dbbasic.py                   # interactive REPL
python src/dbbasic.py --repl            # interactive REPL
```

Flags that the command line (`main()`) recognises:

| Flag | Effect |
|------|--------|
| `--debug` | Turns on interpreter debug mode. |
| `--dump-tokens` | Prints every token the lexer produced before the program runs. |

The command line handles a file in this order:

1. Read the file as UTF-8.
2. Expand `INCLUDE` lines (`preprocess_includes`), resolving names relative to the
   directory that holds the main program.
3. Join continued lines (`preprocess_continuations`).
4. Make the lexer. It changes CRLF line endings to LF, rewrites `ECHO` lines
   (`preprocess_echo_statements`) and then tokenizes the result.
5. Make the interpreter. Before anything runs, it pre-scans the tokens for
   block structure (`IF`/`END IF`, `DO`/`LOOP`), labels and `FUNCTION`
   definitions.
6. Run the program from the first token.

Errors found while tokenizing are printed as `Error: ...`. Errors raised while
the program runs are printed as `Runtime Error: ... at line L, col C.`, followed
by a context line. Both go to standard error.

`--dump-tokens` shows what the lexer produced:

```basic
x = 1 + 2
```

```
--- TOKEN DUMP ---
('ID', 'x', 0)
('ASSIGN', '=', 2)
('NUMBER', '1', 4)
('OP', '+', 6)
('NUMBER', '2', 8)
('NEWLINE', '\n', 9)
--------------------
```

## 1.2 Program structure and source format

A DbBasic program is a plain text file. Statements run from top to bottom.

- **No line numbers.** A line that starts with a number is an error
  (`Unknown statement: NUMBER`). Use labels for jump targets.
- **One or more statements per line.** A colon (`:`) separates statements on the
  same line. A newline ends the last statement on the line. Blank lines are
  allowed anywhere.
- **Whitespace.** Spaces, tabs and non-breaking spaces (U+00A0) between tokens
  are ignored. Indentation has no meaning.
- **Labels.** An identifier followed directly by a colon is a label
  (`name:`). A statement can follow it on the same line. `GOTO`, `GOSUB` and
  `ON ERROR GOTO` use labels (see Chapter 2). Label names are case-sensitive.
- **Program end.** The program stops at the end of the file or at an `END`
  statement. `END` stops the interpreter immediately.

Syntax:

```
[label:] statement [: statement ...]
```

Example:

```basic
REM Program structure demo
total = 0                     -- running total
FOR i = 1 TO 3: total = total + i: NEXT
PRINT "Total:"; total
message$ = "Values " + _
           "joined " + _
           "across lines"
PRINT message$
END
PRINT "never printed"
```

Output:

```
Total: 6
Values joined across lines
```

> **Label pitfall.** The label scanner treats *every* identifier that is
> directly followed by a colon as a label, including one at the end of a
> statement on a multi-statement line. If two such places use the same
> identifier, the program will not start:
>
> ```basic
> b = 1
> a = b: c = b: PRINT a + c
> ```
>
> ```
> Error: Duplicate label found: b at line 1, col 1.
> ```
>
> You can avoid it by putting a space before the colon (`a = b : c = b`) or by
> putting the statements on separate lines.

## 1.3 Comments

DbBasic has two comment forms. Both run to the end of the line, and both can
start a line or follow a statement.

| Form | Example |
|------|---------|
| `REM` text | `REM initialise counters` |
| `--` text | `x = 0  -- reset` |

```basic
REM a full-line comment
-- another full-line comment
PRINT "d" -- trailing comment
PRINT "x" REM trailing REM also works
PRINT "e" : REM after a colon
```

Output:

```
d
x
e
```

Notes:

- `REM` must be a whole word. `REMARK = 1` is a variable assignment, not a comment.
- `--` starts a comment wherever it appears outside a string. This means that
  `5--3` is read as `5` followed by a comment. Write `5 - -3` instead
  (which gives `8`).
- **A single quote (`'`) does not start a comment.** A lone `'` is a lexer error
  (`Unexpected character '''`). A pair of single quotes on a line becomes an
  unusable token (see [1.17](#117-implementation-notes--discrepancies)).

## 1.4 Source preprocessing

Three text-level passes run before tokenizing.

### 1.4.1 INCLUDE

```
INCLUDE "filename"
```

**Description.** The `INCLUDE` line is replaced with the full text of the named
file. This happens before anything else, so the included code acts as if it
had been typed in place.

**Parameters.** `filename` is a double-quoted literal path. It cannot be an
expression. It is resolved relative to the directory of the file that contains
the `INCLUDE`.

**Behaviour.**

- `INCLUDE` must be the first thing on its line (leading whitespace is allowed).
  The keyword is not case-sensitive.
- Included files are processed recursively, so they can contain their own
  `INCLUDE` lines. Nested paths are resolved relative to the included file's
  own directory.
- A file that has already been included, including the main program file,
  is not included again. Its line is replaced with
  `REM SKIPPING CIRCULAR INCLUDE: "name"`.
- The included text is wrapped in `REM <<< START INCLUDE: "file"` and
  `REM <<< END INCLUDE: "file"` marker lines.
- If the file is missing, the line is replaced with
  `ERROR 2, "INCLUDE file not found: ..."`, which raises a runtime error when
  the program reaches it.

**Example.** `lib.bas`:

```basic
PRINT "from lib"
```

`main.bas`:

```basic
INCLUDE "lib.bas"
PRINT "main"
```

```
from lib
main
```

A missing file:

```basic
PRINT "before"
INCLUDE "missing.bas"
PRINT "after"
```

```
before
Runtime Error: Error 2: INCLUDE file not found: missing.bas in folder /path/to/missing.bas
```

### 1.4.2 Line continuation

```
part of a statement _
    rest of the statement
```

**Description.** An underscore (`_`) that is the *last character* on a line
joins that line to the next one. The `_` and the newline become one space.

**Behaviour** (`preprocess_continuations`):

- The `_` must come directly before the newline. If there is whitespace after
  it, it is not a continuation: the `_` is read as an identifier and the next
  line is parsed on its own.
- An underscore inside a double-quoted or backtick string is never a
  continuation.
- An underscore inside a `REM` or `--` comment is never a continuation.
- Continuation works anywhere in a statement: in expressions, in long
  `IF` conditions and between string pieces.

Example (from `examples/continuation.bas`):

```basic
x = 10 + _
    20 + _
    30
PRINT "x = "; x

IF x > 50 _
   AND x < 100 _
   THEN
    PRINT "Complex condition met"
END IF

query$ = `SELECT * FROM table ` _
         + `WHERE id > 0`
PRINT "Query: "; query$
```

Output:

```
x =  60
Complex condition met
Query: SELECT * FROM table WHERE id > 0
```

### 1.4.3 ECHO

```
ECHO [any text to the end of the line]
```

**Description.** `ECHO` prints the rest of its line exactly as written. No
quotes are needed and nothing is evaluated. On its own, `ECHO` prints an empty
line.

**Behaviour** (`preprocess_echo_statements`):

- Any line whose first non-blank word is `ECHO` (in any case) is
  rewritten before tokenizing. The text after `ECHO`, with trailing whitespace
  removed, becomes a double-quoted string. Embedded `"` characters are kept.
- Everything after `ECHO` is literal, including `:`, `${...}`, `REM` and `--`.
  So `ECHO` cannot be followed by another statement on the same line.
- `ECHO` only works as the first statement on a line. `IF 1 THEN ECHO hi` fails
  with `Expected token STRING`.
- `ECHO` must be a whole word. A line that starts with a longer name, such as
  `echo_count = 5` or `echoes$ = "x"`, is an ordinary statement.

```basic
name$ = "x"
ECHO Hello, "world" & friends ${name$} : PRINT "not run"
ECHO
   echo   indented echo
PRINT "done"
```

Output:

```
Hello, "world" & friends ${name$} : PRINT "not run"

indented echo
done
```

## 1.5 The lexer

The `Lexer` class turns the prepared source into a list of tokens. Each token
is a `(kind, value, position)` triple. The token kinds are shown by
`--dump-tokens` and appear in error messages.

The lexer first joins some two-word keywords into single tokens, ignoring case:
`END IF`, `LINE INPUT`, `END LOOP`, `FOR EACH`, `END TRANSACTION`,
`READ FILE`, `TO FILE`, `INTO FILE`, `ANALYZE CSV/FIXED/JSON/JSONL/XML/TEXT`,
`ON ERROR GOTO`, `END FORM`, `OPEN FORM`, `END FUNCTION`, `WITH DETAILS`,
`WITH FULLPATH`, `WITH FOLDERSONLY`, `WITH FILESONLY` and `LIST FIELDS`. You can
write them with any amount of space between the words, and also run together
(`ENDIF`, `FOREACH`).

Punctuation tokens:

| Token | Characters |
|-------|-----------|
| `ASSIGN` | `=` (assignment, and also the equality operator in conditions) |
| `OP` | `+ - * /` |
| `CARET` | `^` |
| `AMPERSAND` | `&` |
| `RELOP` | `<> <= >= < >` |
| `HASH_SYM` | `#` (file numbers, for example `PRINT #1, ...`) |
| `LPAREN` / `RPAREN` | `(` `)` |
| `LBRACKET` / `RBRACKET` | `[` `]` |
| `COMMA`, `SEMICOLON`, `COLON`, `DOT` | `, ; : .` |
| `NEWLINE` | end of line |

Any other character in BASIC code, such as `%`, `!`, `\`, `@`, `?` or `|`,
stops the program before it runs with
`Error: Unexpected character 'c' at line L, col C`. Inside strings, comments and
SQL statements (including SQL subqueries) any character is allowed, so SQL
operators such as `||` and `~` work (see 4.2.1).

### 1.5.1 Keywords and reserved words

Keywords are not case-sensitive (`print`, `Print` and `PRINT` are the same).
A keyword is matched only as a whole word. It is also not matched if a `$`
follows it, so `TEXT$`, `TITLE$` and `SIZE$` are ordinary variable names.

These words are keyword tokens and **cannot be used as plain (non-`$`)
variable names**:

```
ACTION ALTER AND APIKEY APPEND ARRAY AS ATTACH BCC BEGIN BELL BODY BROWSER
BUTTON CC CHAIN CHDIR CHOICE CLEAR CLOSE COMMIT COPY CREATE CSV DATABASE
DELETE DESCRIBE DETAILS DIM DISPLAY DO DOMAIN DROP DUMP ECHO ELSE ELSEIF
EMAIL END ERROR EVAL EXCEL EXECUTE EXISTS EXIT FETCH FIELD FILES FIXED FOR
FORM FUNCTION GOSUB GOTO GRIDEDIT HASH HEADING HELP HOST HTML HTMLBODY IF
IGNORE IN INPUT INSERT INTO JSON JSONL KILL LABEL LET LOAD LOOKUP LOOP MATCHES
MAXLENGTH MERGE MESSAGE MINLENGTH MINVALUE MKDIR NEXT NOT OPEN OPTIONS OR
OUTPUT PARQUET PARSE PASSWORD PATTERN PLACEHOLDER PLAIN POP PORT POST PRAGMA
PRINT PROVIDER PUSH READONLY REDIM REDIRECT REM REPLACE REQUIRED RESUME RETURN
RETURNS REVERSE RMDIR ROLLBACK RUN SEARCH SECURITY SELECT SENDER SEPARATOR SET
SHELL SHIFT SHOW SIZE SORT SOURCE SPLICE STEP SUBJECT SUMMARIZE TABLE TEXT
TEXTBLOCK THEN TITLE TO TROFF TRON TRUNCATE TYPE UNPACK UNSHIFT UNTIL UNZIP
UPDATE UPGRADE UPSERT USER USING WEND WHILE WITH WRITE XML ZIP
```

Many ordinary words are on this list (`user`, `size`, `type`, `title`, `label`,
`message`, `source`, `body`, `host`, `port`, `text`), so this is easy to hit:

```basic
user = 1
```

```
Runtime Error: Unknown statement: USER at line 1, col 1.
```

There are two ways round it. Add a `$` suffix (for a string variable). Or use
the word as a hash key after a dot, which is allowed (`h.user = "u"`,
`h.size = 3`).

Some words are not keyword tokens but still have meaning in certain places.
`ON`, `ASC` and `DESC` are only special inside `SORT`. `NAME` and `COPY` are
special when they start a statement. `NAME = "x"` fails because `NAME` at the
start of a statement is the file-rename command (Chapter 6).

### 1.5.2 Identifiers and the `$` sigil

```
identifier ::= letter_or_underscore { letter | digit | "_" } [ "$" ]
```

- Identifiers begin with a letter or `_`, followed by letters, digits and `_`.
- A trailing `$` is part of the name: `name` and `name$` are **different**
  variables.
- `$` is the only type sigil. Classic BASIC sigils such as `%`, `!`, `#` and `&`
  are not supported. `%` and `!` are lexer errors, and `#` and `&` are operators.
- The `$` suffix sets the **default value** of a variable that has not been
  assigned yet (`""` for `name$`, `0` for `name`). It also sets the fill value
  used by `DIM name$(n)`, by `REDIM`, and when an array grows because of an
  assignment past its end. It does **not** restrict what the variable can hold.
  `s$ = 42` stores the number 42.

### 1.5.3 Numeric literals

```
number ::= digits [ "." [ digits ] ]
```

- Literals are written in decimal: `42`, `3.14159`, `10.` (the same as `10`).
- There is no leading-dot form (`.5` is a syntax error; write `0.5`), no
  exponent form (`1e3` is read as `1` followed by an identifier `e3`), and no
  hex or octal.
- Negative numbers are made with the unary minus operator (`-5`).
- All numeric literals are stored as double-precision floats. Whole numbers are
  printed without a decimal part (`PRINT 2.50 + 0` prints ` 2.5`, and
  `PRINT 10.` prints ` 10`).

### 1.5.4 String literals

There are two kinds of string literal:

| Delimiter | Escapes | Interpolation | May span lines |
|-----------|---------|---------------|----------------|
| `"..."` | `""` gives one `"` | No | No (ends at the closing quote) |
| `` `...` `` | none (a backtick cannot appear inside) | Yes, `${expr}`, with `$$` giving `$` | Yes |

```basic
PRINT "She said ""hi"""
PRINT "No ${name$} interpolation here"
t$ = `line one
line two`
PRINT t$
```

Output:

```
She said "hi"
No ${name$} interpolation here
line one
line two
```

Single-quoted text (`'abc'`) is **not** a DbBasic string literal. Single quotes
are only for SQL string literals inside embedded SQL (Chapter 4). Using one in
a DbBasic expression gives `Unexpected token in factor: ('SINGLE_Q_STRING', ...)`.

### 1.5.5 Backtick strings and `${expr}` interpolation

Inside a backtick string:

- `${expr}` is replaced by the value of `expr`. The expression is tokenized and
  evaluated with the full expression parser in the current scope. It can use
  variables, arithmetic, built-in functions, user-defined functions, hash and
  array access, and scalar SQL subqueries.
- `$$` gives a literal `$`.
- A `$` not followed by `{` or `$` is kept as it is (`` `cost: $5` `` gives
  `cost: $5`).
- `{` and `}` on their own are literal, so JSON and code snippets can be
  written directly.
- Values are formatted for the result as follows. Whole numbers have no
  decimal part, other numbers print normally, a missing value (`None`) becomes
  empty, and arrays and hashes appear in their Python form.
- Errors: an unclosed `${` gives `Unclosed '${' in interpolated string`, and an
  empty `${}` gives `Empty interpolation`. Leftover tokens give
  `Unexpected '...' after interpolation expression`.

```basic
name$ = "Ada"
amount = 1234.5
PRINT `Hello, ${name$}! Total: ${FORMAT$(amount, "$#,##0.00")}`
PRINT `Price: $$${amount * 2} {literal braces}`
PRINT `Sum: ${1 + 2}, upper: ${UCASE$(name$)}`
x = 3
PRINT `${x / 2}`
PRINT `n=${(SELECT 5;)}`
```

Output:

```
Hello, Ada! Total: $1,234.50
Price: $2469 {literal braces}
Sum: 3, upper: ADA
1.5
n=5
```

> The interpolated expression ends at the **first** `}`. An expression that
> itself contains `}` (for example `${"}"}`) cannot be written.

### 1.5.6 Embedded SQL in the token stream

The lexer also finds embedded SQL. That is covered fully in Chapter 4; this
section only describes its effect on tokenizing.

- **SQL statements.** If a statement starts with `SELECT`, `INSERT`, `DELETE`,
  `UPDATE`, `CREATE`, `DROP`, `ATTACH`, `COPY`, `WITH`, `BEGIN`, `COMMIT`,
  `ROLLBACK`, `END TRANSACTION`, `ALTER`, `SUMMARIZE` or `PRAGMA`, everything up
  to the next `;` (even several lines later) becomes one `SQL_STRING` token.
- **Subqueries.** If `(` is directly followed by a SQL keyword, and the `(`
  comes after `=`, `IN`, `EXISTS` or another `(`, the text up to the matching
  `)` becomes a `SQL_STRING` token. This is what makes
  `x = (SELECT ...)` work (see [1.8](#18-assignment-let)).

## 1.6 Data types

DbBasic values are Python values underneath. `TYPENAME$(value)` reports the
type.

| Type | `TYPENAME$` | Literal / constructor | Default for an unset variable |
|------|-------------|----------------------|-------------------------------|
| Number | `FLOAT` | `42`, `3.5` | `0` (name without `$`) |
| String | `STRING` | `"text"`, `` `text` `` | `""` (name ending in `$`) |
| Array | `ARRAY` | `ARRAY(...)`, `DIM a(n)`, `DIM a AS ARRAY` | - |
| Hash | `HASH` | `DIM h AS HASH`, or a dot assignment (`h.k = v`) | - |

**Numbers.** All arithmetic uses floating point (`0.1 + 0.2` gives
`0.30000000000000004`). Integers that come back from SQL keep their integer
form, but they behave the same in expressions.

**Strings** are Unicode text.

**Arrays** are ordered lists indexed from 0. Each element can be any type,
including another array or a hash.

**Hashes** are dictionaries with string keys that keep their insertion order.
Each value can be any type.

**Booleans.** There is no separate boolean type. Comparisons and logical
operators return `-1` for true and `0` for false (see
[1.15](#115-expressions-and-truth-values)).

**NULL.** There is no NULL literal in DbBasic (`NULL` on its own is just an
unset numeric variable, so it is `0`). SQL `NULL` values are handled like this:

- When a scalar subquery or another expression that returns NULL is
  *assigned* to a variable, the variable gets that variable's default value
  instead: `""` for a `$` name, `0` otherwise.

  ```basic
  v = (SELECT NULL)
  v$ = (SELECT NULL)
  PRINT "["; v; "]"; "["; v$; "]"
  ```

  ```
  [ 0][]
  ```

- When NULL is used *directly* inside an expression it is not converted. For
  example, `PRINT (SELECT NULL) + 1` prints `None1`, because `+` falls back to
  string concatenation. Assign the value first, or use `NVL` (Chapter 3).
- Parsed JSON `null` becomes `""`, and JSON `true`/`false` become `-1`/`0`.
- How empty strings are written to database columns is controlled by
  `SET NULL_HANDLING` (Chapter 4).

## 1.7 Variables and scope

- Variables do not need to be declared. Reading a variable that does not exist
  **creates** it with its default value (`0` or `""`).

  ```basic
  PRINT "["; undefined$; "]"
  PRINT undefinedNum
  ```

  ```
  []
   0
  ```

- Variables are dynamically typed: a variable can hold a number, then a string,
  then an array.
- **Scope.** Main program code, subroutines (`GOSUB`) and included code all
  share one global set of variables. In a user-defined function, parameters and
  any names declared with `DIM` inside the body are local: a variable with the
  same name outside the function is saved when the call starts and put back
  when it ends. Every other name used inside a function is global (see
  Chapter 2).
- **Collections are references.** Assigning an array or hash to another
  variable does not copy it. Both names then refer to the same object.

  ```basic
  a = ARRAY(1, 2)
  b = a
  PUSH b, 3
  PRINT a
  ```

  ```
  [ 1,  2,  3]
  ```

- `CLEAR` deletes every variable.

  ```
  CLEAR
  ```

  ```basic
  x = 1: CLEAR: PRINT x
  ```

  ```
   0
  ```

- `SHOW VARIABLES` lists all variables with their Python types. It is useful
  for debugging (Chapter 4).

## 1.8 Assignment: LET

```
[LET] variable = expression
[LET] variable(index_or_key) = expression
[LET] variable.key[.key ...] = expression
[LET] variable = (SELECT ... [;])
```

**Description.** Stores the value of an expression in a variable, in an
array element or in a hash entry. The `LET` keyword is optional.

**Parameters.**

- `variable`: an identifier. It cannot be a keyword (see
  [1.5.1](#151-keywords-and-reserved-words)).
- `expression`: any arithmetic or string expression (see
  [1.14](#114-operators-and-precedence)).

**Behaviour.**

- *Simple form.* Assigns to the variable whose name matches exactly. If the
  value is a missing value (for example SQL NULL), the variable's default is
  stored instead.
- *Index/key form* `v(i) = x`. `v` must already exist (exact name) as an array
  or a hash. Otherwise the error is `'v' is not an array or hash.`
  - Array: `i` is converted to an integer (by truncation). If `i` is beyond the
    end, the array grows and new slots are filled with `""` or `0`, depending
    on `v`'s `$` suffix. A negative `i` counts from the end of the array
    (Python behaviour).
  - Hash: `i` is converted to a key string (whole numbers become `"1"`, not
    `"1.0"`). Its case is kept, or the key is uppercased under
    `SET HASH_KEYS IGNORE_CASE`.
- *Dot form* `v.a.b = x`. If `v` does not exist, or is not a hash, it is
  **replaced by a new empty hash**. Each intermediate key is created as a
  nested hash if it is missing or not a hash. Keys can be keyword words
  (`h.size`, `h.user`).
- Only one level of index is supported on the left-hand side. `g(0)(1) = 5` and
  `p(0).name = "x"` are errors. To change a nested element, copy a reference
  first (`q = p(0): q.name = "x"`). Because collections are references, this
  changes the original.
- *Scalar SQL subquery.* If the right-hand side starts with `(` followed by a
  SQL keyword, the SQL up to the matching `)` runs against the current
  database. It must return exactly one row and one column, or the error is
  `Scalar subquery must return one row/column.` A trailing `;` inside the
  parentheses is optional. Bind variables such as `:name` are replaced by
  DbBasic variable values (Chapter 4).
- `=` in a LET statement is always assignment. `x = a = b` is **not** a
  comparison and fails. To store a truth value, put the comparison in
  parentheses: `x = (a = b)`.

**Examples.**

```basic
LET x = 10
name$ = "Bob"
LET cfg.debug = -1
PRINT x; " "; name$; " "; cfg.debug
DIM nums(3)
nums(0) = 10: nums(1) = 20
nums(6) = 70
PRINT nums
```

Output:

```
 10 Bob -1
[ 10,  20,  0,  0,  0,  0,  70]
```

Scalar subqueries:

```basic
DATABASE OPEN ":memory:"
CREATE TABLE t (n INTEGER, label TEXT);
INSERT INTO t VALUES (1, 'one'), (2, 'two'), (3, 'three');
cnt = (SELECT COUNT(*) FROM t;)
LET biggest$ = (SELECT label FROM t ORDER BY n DESC LIMIT 1)
min_n = 2
above = (SELECT COUNT(*) FROM t WHERE n >= :min_n)
PRINT cnt; " rows, biggest="; biggest$; ", above="; above
```

Output:

```
 3 rows, biggest=three, above= 2
```

## 1.9 Declarations: DIM and REDIM

### DIM

```
DIM name                         -- scalar: 0, or "" for name$
DIM name(size)                   -- fixed array with elements 0..size
DIM name()                       -- empty array
DIM name AS ARRAY                -- empty array
DIM name AS HASH                 -- empty hash
DIM decl [, decl ...]            -- several declarations at once
```

**Description.** Creates (or re-creates) a variable with a starting value.

**Parameters.** `size` is any numeric expression, converted to an integer. The
array gets `size + 1` elements, with indexes 0 to `size`.

**Behaviour.**

- `DIM name(size)` fills the array with `""` if the name ends in `$`, otherwise
  with `0`.
- Using `DIM` on an existing variable **resets** it. `x = 10: DIM x` leaves
  `x` at `0`.
- `AS` followed by anything other than `HASH` or `ARRAY` (for example
  `DIM x AS INTEGER`) is accepted, but **no variable is created**.
- Inside a user-defined function, `DIM` declares a local variable (Chapter 2).
- DIM is optional for scalars and for arrays built with `ARRAY(...)`. It is
  needed before an index/key assignment such as `h("k") = v` on a new variable.

**Examples.**

```basic
DIM a, b$, c(2), d AS HASH
PRINT a; "|"; b$; "|"; c; "|"; d
n = 4
DIM z(n * 2)
PRINT UBOUND(z)
DIM e()
PRINT e; UBOUND(e)
```

Output:

```
 0||[ 0,  0,  0]|{}
 8
[]-1
```

### REDIM

```
REDIM name(size)
```

**Description.** Replaces an existing array with a new array of `size + 1`
default elements.

**Behaviour.**

- `name` must already exist as an array, and the name must match **exactly**,
  including case. Otherwise the error is `'name' not dimensioned for REDIM.`
- The existing contents are **not kept**. Every element is reset to `""` or `0`.

```basic
DIM squares(4)
FOR i = 0 TO UBOUND(squares)
    squares(i) = i * i
NEXT
PRINT squares
REDIM squares(2)
PRINT squares
```

Output:

```
[ 0,  1,  4,  9,  16]
[ 0,  0,  0]
```

## 1.10 Arrays

**Creating arrays.**

| Form | Result |
|------|--------|
| `a = ARRAY(v1, v2, ...)` | array holding the given values, starting at index 0 |
| `a = ARRAY()` | empty array |
| `DIM a(n)` | `n + 1` default elements |
| `DIM a AS ARRAY` / `DIM a()` | empty array |
| `SPLIT(s$, delim$)`, `HASH_KEYS(h)`, `FILTER`, `MAP`, ... | functions that return arrays (Chapter 3) |

There is no bracket literal syntax. The `[` and `]` tokens are not used in
DbBasic expressions.

**Indexing.** `a(i)` reads element `i` (indexes start at 0). The index is
converted to an integer by truncation. A read outside `0..UBOUND(a)`, including
a negative index, gives `Array index out of bounds.` Writes past the end grow
the array (see [1.8](#18-assignment-let)).

**Whole-array references.** A bare name (`a`) or a name with empty parentheses
(`a()`) gives the array itself. That is how arrays are passed to functions:
`UBOUND(a)` and `UBOUND(a())` mean the same thing.

**Nested structures.** Elements can be arrays or hashes. Chained access works
when reading:

```basic
grid = ARRAY(ARRAY(1, 2), ARRAY(3, 4))
PRINT grid(1)(0)
h.k = ARRAY(5, 6)
PRINT h.k(1)
PRINT ARRAY(1, "two", ARRAY(3))
```

Output:

```
 3
 6
[ 1, two, [3.0]]
```

`PRINT` shows an array in brackets. Numeric elements get the same leading
space that `PRINT` gives positive numbers. Nested arrays are shown in their
raw form.

Useful array functions (described in Chapter 3): `UBOUND` (highest index, or
`-1` if empty), `ARRAY_SIZE`, `ARRAY_JOIN`, `SPLIT`, `FILTER`, `MAP`, `REDUCE`.

## 1.11 Hashes

A hash maps string keys to values.

**Creating hashes.**

```basic
DIM h AS HASH        -- explicit
h.key = value        -- also creates h automatically if it is not already a hash
```

**Two access syntaxes.**

| Syntax | Read | Write | Key matching |
|--------|------|-------|--------------|
| `h("key")` / `h(expr)` | yes | yes (one level, `h` must already be a hash) | exact case, unless `SET HASH_KEYS IGNORE_CASE` |
| `h.key` / `h.a.b.c` | yes | yes (auto-creates nested hashes) | reads: exact first, then case-insensitive; writes: key case kept as written |

- With parentheses, the key can be any expression. Whole numbers are converted
  to strings without `.0` (`m(1)` and `m(2.0)` use keys `"1"` and `"2"`).
- **Missing keys** do not raise an error. They give a default value. With
  dot access the default is `""` if the key name ends in `$` (`h.name$`),
  otherwise `0`. With parentheses the default is `""` if the *key text* ends in
  `$` (`h("name$")`), otherwise `0`.
- After a dot, the key name can be an identifier or a keyword word
  (`h.size`, `h.user`, `h.type`). It cannot be punctuation, a number or a
  string.
- The two forms can be mixed: `person("address").zip`, `cfg.tags(0)`.
- `PRINT h` shows the hash as indented JSON.

Example:

```basic
DIM person AS HASH
person.name = "Alice"
person.address.city = "Tampa"
person.address.zip = "33602"
person.tags = ARRAY("admin", "dev")
PRINT person.name; " lives in "; person.address.city
PRINT "First tag: "; person.tags(0)
PRINT "Zip via parens: "; person("address").zip
PRINT person
```

Output:

```
Alice lives in Tampa
First tag: admin
Zip via parens: 33602
{
  "name": "Alice",
  "address": {
    "city": "Tampa",
    "zip": "33602"
  },
  "tags": [
    "admin",
    "dev"
  ]
}
```

### SET HASH_KEYS

```
SET HASH_KEYS PRESERVE_CASE | IGNORE_CASE
```

**Description.** Chooses how hash keys are stored and looked up when you use
parentheses or dot assignment. `PRESERVE_CASE` is the default.

**Behaviour.**

- `PRESERVE_CASE`: keys are stored as written. `h("Name")` and `h("NAME")` are
  different keys. A dot read (`h.name`) still falls back to a case-insensitive
  match.
- `IGNORE_CASE`: keys used through parentheses and dot assignment are
  **uppercased**, so different spellings of a key go to the same entry. JSON
  data parsed while this mode is on also gets uppercased keys.
- The setting applies from the moment it runs. It does not change keys that
  already exist.

```basic
SET HASH_KEYS IGNORE_CASE
DIM p AS HASH
p.itemName = "Widget"
p("ItemName") = "Gadget"
PRINT p
PRINT p("itemname")
```

Output:

```
{
  "ITEMNAME": "Gadget"
}
Gadget
```

Useful hash functions (Chapter 3): `HASH_COUNT`, `HASH_KEYS`, `HASH_EXISTS`,
`JSON_SERIALIZE$`.

## 1.12 Array statements

All of these statements change the array **in place**. The array name must
match an existing array variable **exactly** (including case), or the error is
`'name' is not an array.`

> **1-based SHIFT/UNSHIFT.** `UNSHIFT` and `SHIFT` work on index **1**, not
> index 0. The source treats element 0 as a reserved slot. This suits arrays
> made with `DIM a(n)` and used from index 1, but it is surprising for arrays
> made with `ARRAY(...)` or `PUSH`, which start at index 0. `PUSH`, `POP`,
> `SPLICE`, `REVERSE` and `SORT` work on the whole array, including index 0.

### PUSH

```
PUSH array, expression
```

Adds the value to the end of the array.

### POP

```
POP array [INTO variable]
```

Removes the last element. With `INTO`, the removed value is stored in
`variable`. Popping an empty array is an error
(`Cannot POP from empty array 'a'.`).

```basic
stack = ARRAY()
PUSH stack, 10
PUSH stack, 20
PUSH stack, 30
POP stack INTO top
PRINT top; " left:"; stack
```

Output:

```
 30 left:[ 10,  20]
```

### UNSHIFT

```
UNSHIFT array, expression
```

Inserts the value at **index 1**, moving the existing element 1 and later ones
up by one. Element 0 is not touched. On an empty array the value goes to
index 0.

### SHIFT

```
SHIFT array [INTO variable]
```

Removes the element at **index 1**, optionally storing it in `variable`. The
array must have at least two elements, or the error is
`Cannot SHIFT from empty array 'a'.`

```basic
q = ARRAY("x", "a", "b")
PRINT q
UNSHIFT q, "NEW"
PRINT q
SHIFT q INTO removed$
PRINT removed$; " -> "; q
```

Output:

```
[x, a, b]
[x, NEW, a, b]
NEW -> [x, a, b]
```

### SPLICE

```
SPLICE array, start, count [, value1, value2, ...]
```

Removes up to `count` elements starting at index `start` (0-based). Any values
given are then inserted at `start`, in order. `start` must be between 0 and the
array length; `start` equal to the length appends to the end. Any other value
is an error (`SPLICE start index N out of bounds.`). `count` can be 0, which
only inserts.

```basic
colors = ARRAY("red", "green", "blue", "cyan")
SPLICE colors, 1, 2
PRINT colors
SPLICE colors, 1, 0, "lime", "teal"
PRINT colors
SPLICE colors, 4, 0, "end"
PRINT colors
```

Output:

```
[red, cyan]
[red, lime, teal, cyan]
[red, lime, teal, cyan, end]
```

### REVERSE

```
REVERSE array
```

Reverses the order of the elements.

```basic
colors = ARRAY("red", "lime", "teal")
REVERSE colors
PRINT colors
```

Output:

```
[teal, lime, red]
```

### SORT

```
SORT array [ASC | DESC]
SORT array ON key_expression [ASC | DESC]
SORT array WITH function_name [ASC | DESC]
```

**Description.** Sorts the array. The default order is ascending.

**Parameters and behaviour.**

- *Plain:* sorts the elements by their own values. Strings are compared by
  character code, so uppercase sorts before lowercase. If the array mixes
  numbers and strings, the elements are compared as strings instead.
- `ON key_expression`: for an array of hashes. `key_expression` must evaluate to
  a string, which is the hash key to sort by. An element that is not a hash, or
  that lacks the key, sorts as `0`. If the key values have mixed types, they
  are compared as strings.
- `WITH function_name`: the named function (a user-defined function or a
  built-in such as `UCASE$`) is called once for each element. The element is
  sorted by the result. Write the name without parentheses. An unknown name
  gives `SORT WITH: unknown function 'x'.`
- `ON`, `ASC` and `DESC` must be written in **uppercase**. Lowercase `desc` is
  silently ignored, and lowercase `on` is a syntax error.
- An empty array is left as it is.

```basic
names = ARRAY("pear", "Apple", "fig")
SORT names
PRINT names
SORT names DESC
PRINT names
nums = ARRAY(10, 2, 33)
SORT nums
PRINT nums
mixed = ARRAY(10, "b", 2)
SORT mixed
PRINT mixed

DIM a AS HASH
a.name = "Bo": a.age = 40
DIM b AS HASH
b.name = "Al": b.age = 25
people = ARRAY(a, b)
SORT people ON "age"
PRINT people(0).name; " "; people(1).name

FUNCTION keylen(s$)
  keylen = LEN(s$)
END FUNCTION
words = ARRAY("ccc", "a", "bb")
SORT words WITH keylen
PRINT words
```

Output:

```
[Apple, fig, pear]
[pear, fig, Apple]
[ 2,  10,  33]
[ 10,  2, b]
Al Bo
[a, bb, ccc]
```

## 1.13 FOR EACH over a hash

```
FOR EACH key_var IN HASH hash_name
    statements
NEXT [key_var]
```

**Description.** Runs the loop body once for each key of a hash, in insertion
order. In each pass, `key_var` holds the key as a string.

**Behaviour.**

- `hash_name` must be an existing hash with an exactly matching name, or the
  error is `'name' is not a hash.`
- The list of keys is taken when the loop starts. Keys added inside the loop
  are not visited in that run.
- An empty hash skips the body.
- `EXIT FOR` leaves the loop (Chapter 2).
- When the loop ends, `key_var` gets back its value from before the loop, or
  is deleted if it did not exist before.
- `FOR EACH` only works with hashes (`IN HASH` is required). For arrays, use
  `FOR i = 0 TO UBOUND(a)` (Chapter 2).

```basic
DIM scores AS HASH
scores("alice") = 91
scores("bob") = 78
scores("carol") = 85
FOR EACH name$ IN HASH scores
    PRINT name$; ": "; scores(name$)
NEXT
```

Output:

```
alice:  91
bob:  78
carol:  85
```

## 1.14 Operators and precedence

From highest to lowest precedence (as implemented by `_parse_factor`,
`_parse_power`, `_parse_term`, `_parse_expression`, `_parse_comparison`,
`_parse_and_condition` and `_parse_or_condition`):

| Level | Operators | Associativity | Notes |
|-------|-----------|---------------|-------|
| 1 | `( )`, literals, variables, function calls, `a(i)`, `h.k` | - | |
| 2 | unary `-`, unary `+` | right | binds tighter than `^`: `-2^2` is `4` |
| 3 | `^` | **left** | `2^3^2` is `64` |
| 4 | `*` `/` | left | both sides are converted to numbers |
| 5 | `+` `-` `&` | left | see below |
| 6 | `=` `<>` `<` `>` `<=` `>=`, `IN (...)` | none (one per operand pair) | conditions only |
| 7 | `NOT`, `EXISTS (SELECT ...)` | prefix | applies to a whole comparison |
| 8 | `AND` | left | |
| 9 | `OR` | left | |

**Arithmetic.**

- `*`, `/` and `-` convert both operands to numbers. A numeric string such as
  `"4"` is accepted (`3 * "4"` is `12`). A non-numeric string gives
  `Type mismatch: cannot perform arithmetic on 'a' and '2.0'.`
- `/` is always floating-point division (`7/2` is `3.5`). Dividing by zero gives
  `Division by zero`.
- There are no `MOD` or `\` (integer division) operators. Use the `MOD()`
  and `INT()` functions (Chapter 3).
- `^` raises to a power (`x^0.5` is a square root).

**String concatenation.**

- `&` always concatenates. Both sides are turned into text, and whole numbers
  lose their `.0` (`1 & 2` gives `"12"`, `"Total: " & 42` gives `"Total: 42"`).
- `+` **first tries numeric addition**, even on strings that look like numbers.
  It concatenates only if one side cannot be read as a number:

  | Expression | Result |
  |-----------|--------|
  | `"5" + "6"` | `11` |
  | `"5" & "6"` | `"56"` |
  | `"a" + 1` | `"a1"` |
  | `"1" + "2" + "a"` | `"3a"` |

  Use `&` whenever you mean string joining and the values might look numeric
  (for example zip codes, IDs or values read from a file).

**Comparison.**

- `=` and `<>` compare values without converting them: `("1" = 1)` is `0`
  (false).
- `<`, `>`, `<=` and `>=` compare numbers numerically and strings by character
  code, case-sensitively. Comparing a number with a string gives a runtime
  error (`'<' not supported between instances of 'float' and 'str'`).
- `expr IN (v1, v2, ...)` is true if `expr` equals one of the listed values.
  `expr IN (SELECT ...)` tests membership in the first column of the query
  result (Chapter 4).

**Logical.**

- `AND` and `OR` are **logical, not bitwise**. Each side counts as true if it
  is non-zero, and the result is `-1` or `0`. `(2 AND 4)` is `-1`.
- `NOT x` gives `-1` if `x` is zero and `0` otherwise. `NOT` binds more
  loosely than comparison and more tightly than `AND`/`OR`:
  `NOT a = 6` means `NOT (a = 6)`.
- Both sides of `AND`/`OR` are always evaluated (no short-circuit).
  `((1 < 2) OR (1/0))` still raises `Division by zero`.

```basic
a = 2: b = 3: c = 4
PRINT a + b * c ^ 2
PRINT (a + b) * c
PRINT -a ^ 2
PRINT 2 ^ 3 ^ 2
ok = (a < b AND b < c)
PRINT ok
both$ = "Total: " & 42
PRINT both$
```

Output:

```
 50
 20
 4
 64
-1
Total: 42
```

## 1.15 Expressions and truth values

DbBasic has two expression levels, and the difference matters:

- **Value expressions** (`_parse_expression`): arithmetic and concatenation
  only. Used by `LET`/assignment, `PRINT`, function arguments, array indexes,
  `PUSH` and most other statements.
- **Conditions** (`_parse_condition`): value expressions combined with
  comparisons, `IN`, `EXISTS`, `NOT`, `AND` and `OR`. Used by `IF`, `ELSEIF`,
  `WHILE`, `DO ... WHILE/UNTIL` (Chapter 2), and **inside any pair of
  parentheses**.

So a comparison outside `IF`/`WHILE` must be in parentheses:

```basic
x = 3 > 2        -- fails: assigns 3, then "Unknown statement: RELOP"
x = (3 > 2)      -- -1
PRINT (1 <> 2)   -- -1
```

**Truth values.** True is `-1` and false is `0`. When a condition has no
comparison operator, the value is true if it is **not equal to the number 0**.
This means:

| Value | Truth |
|-------|-------|
| `0` | false |
| any other number | true |
| any string, **including `""`** | true |
| array or hash | true |

```basic
a = 5: IF a THEN PRINT "truthy"
IF "" THEN PRINT "empty truthy" ELSE PRINT "empty false"
IF 1 + 2 = 3 AND 2 > 1 THEN PRINT "ok"
PRINT ((1 = 1) AND (2 = 3))
PRINT (NOT 0); (NOT 5)
PRINT (5 IN (1, 5, 9)); ("b" IN ("a", "b"))
```

Output:

```
truthy
empty truthy
ok
 0
-1 0
-1-1
```

To test whether a string is empty, compare it explicitly:
`IF s$ = "" THEN ...` or `IF LEN(s$) = 0 THEN ...`.

**Other factors.** A factor can also be:

- `(SELECT ...)`, a scalar SQL subquery that must return one row and one column;
- `name(args)`, a built-in or user-defined function call (Chapter 3, Chapter 2);
- `DATE$`, `TIME$`, `FREEFILE`, `RND` or `CURDIR$` without parentheses, which
  call the function with no arguments.

## 1.16 Case sensitivity summary

| Element | Case-sensitive? |
|---------|-----------------|
| Keywords (`PRINT`, `for each`, `End If`) | No |
| Built-in function names | No |
| Variable **reads** | No. An exact match is tried first, then the first case-insensitive match. |
| Variable **writes** (simple assignment, `DIM`, `REDIM`, `v(i) =`, `v.k =`) | **Yes.** `count = 1: COUNT = 2` makes two variables. |
| Collection statements (`PUSH`, `POP`, `SHIFT`, `UNSHIFT`, `SPLICE`, `REVERSE`, `SORT`, `FOR EACH ... IN HASH`) | **Yes** (the array/hash name must match exactly) |
| `ON`, `ASC`, `DESC` in `SORT` | **Yes** (uppercase only) |
| Labels (`GOTO Done` vs `done:`) | **Yes** |
| Hash keys with `h("key")` | Yes under `PRESERVE_CASE`. Keys are uppercased under `IGNORE_CASE`. |
| Hash keys with `h.key` (read) | No (exact first, then case-insensitive) |
| String comparison (`"A" = "a"`) | Yes |

```basic
count = 1
COUNT = 2
PRINT count; Count; COUNT
```

Output (`Count` finds `count` through the case-insensitive fallback):

```
 1 1 2
```

**Recommendation:** spell each variable, array and label the same way every
time you use it.

## 1.17 Implementation notes / discrepancies

These were found while checking this chapter against the source and against
the existing documentation:

1. **`'` comments are not supported.** The lexer has no apostrophe-comment rule.
   A lone `'` stops the program with `Unexpected character '''`. Text between
   two single quotes becomes a `SINGLE_Q_STRING` token, which no statement or
   expression accepts. The scripts in `tests/` and `examples/` that used
   `'` comments have been converted to `REM` and `--`.
   The `SORT` entry in the built-in `HELP` uses `` ` `` as a trailing comment
   (`` SORT items WITH sort_key$ ASC      ` UDF returns the key ``), but a
   backtick starts a string, so that example does not work as written.
2. **INCLUDE** (fixed): the preprocessor's marker lines used to start with
   `'`, so every successful include failed (see item 1). They now use `REM`.
   The main program file is also registered, so a circular include can no
   longer pull it in a second time.
3. **ECHO word boundary** (fixed). Any line starting with the letters `ECHO`
   used to be rewritten, so `echo_count = 5` printed `_count = 5`.
4. **Variable writes are case-sensitive but reads are not.** The README and
   `tests/hashtest.bas` describe BASIC variables as case-insensitive. That holds
   for reads only. Assignments, `DIM`, `REDIM` and all array statements use the
   exact spelling.
5. **Reserved words.** `USER` is a reserved keyword token (added for
   `SET EMAIL`), so `DIM user AS HASH` fails. `tests/hashtest.bas` has been
   updated to use `person` instead. Several other
   common words (`size`, `type`, `title`, `label`, `message`, `source`, `text`,
   `body`, `host`, `port`) are also reserved and cannot be used as plain
   variable names.
6. **`SHIFT`/`UNSHIFT` use index 1.** The `HELP` text says "Removes the first
   element" and "Adds an element to the beginning", but the code works on index
   1 ("1 based, so ignore 0"). Arrays made with `ARRAY()`/`PUSH` start at
   index 0.
7. **`DIM x AS <other type>`** (for example `AS INTEGER` or `AS STRING`) is
   accepted but creates no variable.
8. **`SORT` modifiers are case-sensitive.** `ON`, `ASC` and `DESC` are compared
   as uppercase text, so `sort a desc` sorts ascending without any error.
9. **Comparisons are not valid in value expressions** without parentheses
   (`x = a > b`, `PRINT 1 <> 2`). The README's examples only use comparisons
   in `IF`, which is consistent with this.
10. **Label scanning** registers every `identifier:` pair, which can cause
    false `Duplicate label` errors on multi-statement lines (see
    [1.2](#12-program-structure-and-source-format)).
11. **Numeric literals** do not allow a leading `.` or exponents (`.5`, `1e3`).
12. **Unconverted NULL in expressions.** A SQL NULL used directly in an
    expression is the Python `None`, so `(SELECT NULL) + 1` gives `"None1"`.
    Only assignment converts NULL to the variable's default.
13. **`${...}` ends at the first `}`**, so an interpolated expression cannot
    contain a `}` character, even inside a string literal.
14. **Negative array indexes.** Reading `a(-1)` raises "out of bounds", but
    assigning `a(-1) = v` writes to the last element.
