# Chapter 2: Control Flow, Procedures & Program Control

This chapter covers the statements that decide which code runs, how often it runs, and how a DbBasic program is structured into labels, subroutines and user-defined functions. It also covers error trapping, the statements that start or replace other programs, the debugging aids, and how to run the interpreter from the command line or the interactive REPL.

**Contents**

- [2.1 Execution model](#21-execution-model)
- [2.2 Conditions](#22-conditions)
- [2.3 IF ... THEN ... ELSE](#23-if--then--else)
- [2.4 FOR ... TO ... STEP ... NEXT](#24-for--to--step--next)
- [2.5 The FOR ... IN family](#25-the-for--in-family)
- [2.6 FOR EACH ... IN HASH](#26-for-each--in-hash)
- [2.7 WHILE ... WEND](#27-while--wend)
- [2.8 DO ... LOOP](#28-do--loop)
- [2.9 EXIT](#29-exit)
- [2.10 Labels and GOTO](#210-labels-and-goto)
- [2.11 GOSUB and RETURN](#211-gosub-and-return)
- [2.12 User-defined functions (FUNCTION ... END FUNCTION)](#212-user-defined-functions-function--end-function)
- [2.13 Functions as first-class arguments](#213-functions-as-first-class-arguments)
- [2.14 Error handling](#214-error-handling)
- [2.15 Program control: END, RUN, CHAIN, EVAL, EXECUTE, CLEAR](#215-program-control-end-run-chain-eval-execute-clear)
- [2.16 Debugging: TRON, TROFF, DUMP, SHOW VARIABLES](#216-debugging-tron-troff-dump-show-variables)
- [2.17 Running DbBasic](#217-running-dbbasic)
- [2.18 Implementation notes and discrepancies](#218-implementation-notes-and-discrepancies)

Lexical rules, data types, variables, arrays, hashes and operators are covered in Chapter 1. The built-in function catalog is in Chapter 3. SQL statements, `PRINT` and `SET` are in Chapter 4. `LOAD` and `ANALYZE` are in Chapter 5. File I/O, networking and forms are in Chapter 6.

All examples in this chapter were run against `src/dbbasic.py`. The output shown is what the interpreter printed.

---

## 2.1 Execution model

These points about how the interpreter runs a program apply to every statement in this chapter.

- **Statements and lines.** A program is a sequence of lines. One line can hold several statements separated by colons (`:`). Lines are executed top to bottom.
- **Pre-scan.** Before anything runs, the interpreter makes three passes over the token stream:
  1. It records the `IF`/`ELSEIF`/`ELSE`/`END IF` and `DO`/`LOOP` structure in a jump map. An unclosed block `IF` or `DO` is reported immediately as `Mismatched 'IF' on line N without a corresponding closing statement.`
  2. It records every **label**, meaning any identifier directly followed by a colon (see 2.10).
  3. It records every `FUNCTION ... END FUNCTION` definition (see 2.12).

  Because of this pass, you can `GOTO` or `GOSUB` a label defined further down, and you can call a function before its definition appears.
- **Function bodies are skipped.** When the main flow of control reaches a `FUNCTION` definition, it jumps past the matching `END FUNCTION`. Function bodies run only when the function is called.
- **Stopping.** A program stops when it runs out of lines, when it executes `END`, or when an untrapped error occurs. A bare `END` on its own line at the top level also stops the main loop. This is why subroutines and error handlers are usually placed after an `END`.
- **Runtime errors.** An untrapped error prints `Runtime Error: <message>` (or, for some errors, `Error: <message>`) to **stderr**, usually followed by the line, column and a token context. Execution then stops, and the process exits with status 1 (see 2.17).

---

## 2.2 Conditions

`IF`, `ELSEIF`, `WHILE`, `DO WHILE/UNTIL` and `LOOP WHILE/UNTIL` all evaluate a *condition*. A condition is an ordinary expression (Chapter 1) extended with the following forms:

| Form | Meaning |
|---|---|
| `expr` | True when the value is non-zero. Comparisons return `-1` (true) or `0` (false). |
| `a AND b`, `a OR b`, `NOT a` | Logical operators. `NOT` binds tighter than `AND`, which binds tighter than `OR`. The result is `-1` or `0`. |
| `EXISTS (SELECT ...)` | True if the query returns at least one row. |
| `expr IN (v1, v2, ...)` | True if `expr` equals one of the listed values. |
| `expr IN (SELECT ...)` | True if `expr` equals a value in the first column of the query result. |

SQL inside these conditions can use `:name` bind variables to refer to DbBasic variables. Bind variables are described in Chapter 4.

---

## 2.3 IF ... THEN ... ELSE

### Syntax

Single-line form:

```
IF condition THEN statement[ : statement ...] [ELSE statement]
```

Block form:

```
IF condition THEN
    statements
[ELSEIF condition THEN
    statements] ...
[ELSE
    statements]
END IF
```

`ENDIF` (one word) is accepted as a synonym for `END IF`.

### Description

The interpreter chooses the form by looking at what follows `THEN`. If `THEN` is the last token on the line, the statement is a **block IF** and must be closed by `END IF`. Otherwise it is a **single-line IF**. Comments are discarded by the lexer, so a line such as `IF x THEN REM note` is treated as a block IF.

**Block IF.** The conditions are tested in order: first the `IF`, then each `ELSEIF`. The block belonging to the first true condition runs, and execution continues after `END IF`. If no condition is true and there is an `ELSE` block, that block runs. Block IFs can be nested to any depth. `ELSEIF` must be written as one word. Writing `ELSE IF` starts a new single-line `IF` inside the `ELSE` branch.

**Single-line IF.** The behaviour around colons is easy to get wrong:

- **True condition:** the statement after `THEN` runs. If an `ELSE` follows, the `ELSE` statement is skipped up to the next colon or end of line. Any statements after that colon **still run**.
- **False condition:** everything up to the end of the line, or up to `ELSE`, is skipped. If there is an `ELSE`, the statement after it runs, followed by any further colon-separated statements on the line.

In practice:

- When there is no `ELSE`, every colon-separated statement after `THEN` belongs to the IF.
- When there is an `ELSE`, the statements after the `ELSE` branch run whichever branch was taken.

### Example: block IF

```basic
score = 72
IF score >= 90 THEN
  grade$ = "A"
ELSEIF score >= 80 THEN
  grade$ = "B"
ELSEIF score >= 70 THEN
  grade$ = "C"
ELSE
  grade$ = "F"
END IF
PRINT "Grade: "; grade$
IF score > 50 THEN PRINT "pass" ELSE PRINT "fail"
```

```
Grade: C
pass
```

### Example: colons in single-line IFs

```basic
x = 5
IF x > 1 THEN PRINT "A" : PRINT "B"
IF x > 9 THEN PRINT "C" : PRINT "D"
IF x > 9 THEN PRINT "E" ELSE PRINT "F" : PRINT "G"
IF x > 1 THEN PRINT "H" ELSE PRINT "I" : PRINT "J"
```

```
A
B
F
G
H
J
```

On the last line the condition is true, but `J` is still printed.

### IF EXISTS and IN (SELECT ...)

Section 2.2 lists the condition forms. `EXISTS (SELECT ...)` lets you test whether a query returns any rows without fetching them into a variable:

```basic
CREATE TABLE users (id INTEGER, name TEXT);
INSERT INTO users VALUES (1, 'Ann'), (2, 'Bob');
IF EXISTS (SELECT 1 FROM users WHERE name = 'Bob') THEN PRINT "Bob found"
who$ = "Zed"
IF NOT EXISTS (SELECT 1 FROM users WHERE name = :who$) THEN
  PRINT who$; " not found"
END IF
IF 2 IN (SELECT id FROM users) THEN PRINT "id 2 exists"
```

```
Bob found
Zed not found
id 2 exists
```

---

## 2.4 FOR ... TO ... STEP ... NEXT

### Syntax

```
FOR var = start TO end [STEP increment]
    statements
NEXT [var]
```

### Parameters

| Parameter | Description |
|---|---|
| `var` | A numeric loop variable. |
| `start`, `end` | Numeric expressions. Both are evaluated **once**, when the loop starts. |
| `increment` | Optional numeric expression, evaluated once. The default is `1`. It can be negative or fractional. |

### Behaviour

- `var` is set to `start`. Before each pass the loop checks whether to stop: with a positive step it stops when `var > end`, and with a negative step it stops when `var < end`. After each pass, `increment` is added to `var`.
- If the stop condition is already true at the start, the body never runs and `var` keeps the value `start`.
- When a loop finishes normally, `var` holds the first value that failed the test. For example, after `FOR i = 1 TO 3`, `i` is `4`.
- Assigning to `var` inside the body changes the iteration. Changing the variables used in `end` has no effect, because `end` was evaluated once.
- `STEP 0` never satisfies either stop test, so the loop runs forever unless the body uses `EXIT FOR`.
- The variable name after `NEXT` is optional. The interpreter **does not check** that it matches the loop variable.
- A whole loop can be written on one line: `FOR i = 1 TO 3 : PRINT i : NEXT`.

### Example

```basic
FOR i = 1 TO 3
  PRINT "i ="; i
NEXT i
PRINT "after loop, i ="; i
FOR n = 10 TO 1 STEP -4 : PRINT n : NEXT
FOR i = 5 TO 1
  PRINT "never runs"
NEXT
PRINT "skipped loop leaves i ="; i
```

```
i = 1
i = 2
i = 3
after loop, i = 4
 10
 6
 2
skipped loop leaves i = 5
```

> **Caution:** Do not put a `FOR EACH ... NEXT` loop directly inside a `FOR ... TO` loop. See 2.18.

---

## 2.5 The FOR ... IN family

`FOR ... IN` loops step through a data source one record at a time and end with `NEXT`. The interpreter picks the kind of loop from the keyword after `IN`:

| Syntax | Source | Loop variable receives |
|---|---|---|
| `FOR row IN (SELECT ...)` | SQL result set | a HASH for each row |
| `FOR rec IN CSV file$ [OPTIONS opts$]` | CSV file | a HASH for each data row |
| `FOR obj IN JSON(file$)` | JSON file (an array of objects, or a single object) | a HASH or value for each element |
| `FOR obj IN JSONL(file$)` | JSON Lines file | a HASH or value for each non-blank line |
| `FOR line$ IN TEXT(file$)` | plain text file | each line as a string, without its line ending |
| `FOR f$ IN FILES(pattern$ [options])` | directory listing | each file or folder name as a string |

Rules shared by every member of the family:

- **Scope of the loop variable.** If the variable existed before the loop, its earlier value is restored when the loop ends. If it did not exist, it is deleted when the loop ends.
- **`RECNO`.** All loops except `FILES` set the numeric variable `RECNO` to the current record number. `RECNO` is deleted when the loop ends, and reading it afterwards gives `0`. Because of this, an inner `FOR ... IN` loop also removes the outer loop's `RECNO` until the outer loop's next pass. The exact numbering differs by source. See the notes below and 2.18.
- **Empty sources.** If there are no rows, the body is skipped.
- `EXIT FOR` leaves any of these loops. See 2.9 for a caution about `NEXT var` combined with `EXIT FOR`.
- `NEXT` can be followed by the loop variable name. The name is not checked.

Chapters 4, 5 and 6 cover the data formats, CSV options and SQL in depth. This section covers only the loop syntax and what the loop variable contains.

### SQL result sets

```
FOR row IN (SELECT ...)
    statements
NEXT [row]
```

The query runs once, before the first pass. For each row, `row` becomes a HASH with two kinds of key:

- one key per column, named after the column in **upper case**, for example `NAME` and `DEPT`;
- one key per column position, as the strings `"1"`, `"2"`, and so on.

Hash keys are looked up without regard to case, so `row.name`, `row.NAME` and `row("name")` all work. SQL `NULL` values become `""`. `RECNO` counts from 1.

```basic
CREATE TABLE emp (id INTEGER, name TEXT, dept TEXT);
INSERT INTO emp VALUES (1, 'Ann', 'IT'), (2, 'Bob', NULL), (3, 'Cy', 'HR');
min_id = 1
FOR row IN (SELECT id, name, dept FROM emp WHERE id > :min_id ORDER BY id)
  PRINT RECNO; ": "; row.name; " / dept=["; row.DEPT; "] / col1="; row("1")
NEXT
```

```
 1: Bob / dept=[] / col1= 2
 2: Cy / dept=[HR] / col1= 3
```

### CSV files

```
FOR rec IN CSV filename$ [OPTIONS options$]
    statements
NEXT [rec]
```

`filename$` is any string expression. Because it is an expression, both `CSV "f.csv"` and `CSV("f.csv")` work. The loop recognizes only one option: if `options$` contains `header=true` (case-insensitive), the first row is used as column names.

- Every row has positional keys `"1"`, `"2"`, and so on.
- With `header=true`, each row also has keys named after the header cells. Characters other than letters, digits and `_` are removed from the names, so `Unit Price` becomes `UnitPrice`. With `SET HASH_KEYS IGNORE_CASE`, header names are also converted to upper case.
- All values are strings.
- `RECNO` starts at **2** whether or not there is a header. With a header row this equals the physical line number in the file.

Given `items.csv`:

```
name,qty,Unit Price
Widget,3,2.50
Gadget,5,1.25
```

```basic
FOR rec IN CSV "items.csv" OPTIONS "header=true"
  PRINT RECNO; " "; rec.name; " qty="; rec.qty; " price="; rec.UnitPrice
NEXT
FOR rec IN CSV("items.csv")
  PRINT RECNO; " "; rec("1"); " | "; rec("2")
NEXT
```

```
 2 Widget qty=3 price=2.50
 3 Gadget qty=5 price=1.25
 2 name | qty
 3 Widget | 3
 4 Gadget | 5
```

### JSON, JSONL and TEXT files

```
FOR obj IN JSON(filename$)   ... NEXT
FOR obj IN JSONL(filename$)  ... NEXT
FOR line$ IN TEXT(filename$) ... NEXT
```

The file name must be in parentheses.

- **JSON** reads the whole file. The top-level value must be an array; a single object is treated as an array of one. Each element is converted to DbBasic values (objects become HASHes and arrays become ARRAYs). JSON numbers stay numeric. `RECNO` counts from 1.
- **JSONL** reads one JSON document per line and skips blank lines. `RECNO` counts *physical lines*, including the blank lines that were skipped.
- **TEXT** returns each line without its trailing `\n` or `\r\n`. The file is read as UTF-8, and undecodable bytes are replaced rather than causing an error. `RECNO` counts from 1.
- A missing file causes the error `File not found for JSON loop: ...` (or `JSONL`/`TEXT`). Malformed JSON causes `Invalid JSON ...`.

With `items.json` = `[{"id":1,"tag":"red"},{"id":2,"tag":"blue"}]`, `items.jsonl` holding the same two objects separated by a blank line, and `notes.txt` holding two lines:

```basic
FOR obj IN JSON("items.json")
  PRINT RECNO; " id="; obj.id; " tag="; obj.tag
NEXT
FOR obj IN JSONL("items.jsonl")
  PRINT RECNO; " id="; obj.id; " tag="; obj.tag
NEXT
FOR line$ IN TEXT("notes.txt")
  PRINT RECNO; ": "; line$
NEXT
```

```
 1 id= 1 tag=red
 2 id= 2 tag=blue
 1 id= 1 tag=red
 3 id= 2 tag=blue
 1: first line
 2: second line
```

### FILES

```
FOR name$ IN FILES(pattern$ [RECURSIVE] [WITH FULLPATH] [WITH FILESONLY | WITH FOLDERSONLY])
    statements
NEXT [name$]
```

| Option | Effect |
|---|---|
| *(none)* | `pattern$` is a glob pattern (`~` is expanded). If it names a directory, every entry in that directory is listed. |
| `RECURSIVE` | Also searches subdirectories. For a directory this lists `dir/**/*`. For a pattern such as `data/*.txt` it lists `data/**/*.txt`. |
| `WITH FULLPATH` | The variable receives the absolute path instead of just the file name. |
| `WITH FILESONLY` | Lists only regular files. |
| `WITH FOLDERSONLY` | Lists only directories. |

The options go **inside** the parentheses and can appear in any order. Results are sorted by path. This loop does not set `RECNO`.

```basic
FOR f$ IN FILES("data")
  PRINT "entry: "; f$
NEXT
FOR f$ IN FILES("data/*.txt" RECURSIVE WITH FILESONLY)
  PRINT "txt: "; f$
NEXT
FOR d$ IN FILES("data" WITH FOLDERSONLY)
  PRINT "dir: "; d$
NEXT
```

```
entry: a.txt
entry: b.txt
entry: sub
txt: a.txt
txt: b.txt
txt: c.txt
dir: sub
```

(Here `data/` contains `a.txt`, `b.txt` and the folder `sub/`, which holds `c.txt`.)

---

## 2.6 FOR EACH ... IN HASH

### Syntax

```
FOR EACH key IN HASH hashvar
    statements
NEXT [key]
```

### Description

Runs the body once for each key of the HASH variable `hashvar`, in insertion order, with `key` set to the key string. The keys are captured when the loop starts, so adding or removing keys inside the body does not change which keys are visited. Read the value with `hashvar(key)`.

- `hashvar` must already be a HASH. Otherwise the error is `'name' is not a hash.`
- An empty hash skips the body.
- As with `FOR ... IN`, the earlier value of `key` is restored when the loop ends, or `key` is deleted if it did not exist before.
- `EXIT FOR` leaves the loop.

### Example

```basic
DIM stock AS HASH
stock("apples") = 12
stock("pears") = 0
stock("plums") = 7
FOR EACH fruit$ IN HASH stock
  PRINT fruit$; " = "; stock(fruit$)
NEXT
PRINT "fruit$ after loop: ["; fruit$; "]"
```

```
apples =  12
pears =  0
plums =  7
fruit$ after loop: []
```

---

## 2.7 WHILE ... WEND

### Syntax

```
WHILE condition
    statements
WEND
```

### Description

The condition is tested before each pass. While it is true (non-zero), the body runs. If it is false the first time, the body is skipped. `EXIT WHILE` leaves the loop. There is no `END WHILE` alternative.

### Example

```basic
balance = 100
years = 0
WHILE balance < 150
  balance = balance * 1.1
  years = years + 1
WEND
PRINT "Years:"; years; " Balance:"; ROUND(balance, 2)
n = 0
WHILE -1
  n = n + 1
  IF n = 3 THEN EXIT WHILE
WEND
PRINT "n ="; n
```

```
Years: 5 Balance: 161.05
n = 3
```

> **Caution:** Do not put a `DO WHILE` or `LOOP WHILE` inside a `WHILE ... WEND` body. See 2.18.

---

## 2.8 DO ... LOOP

### Syntax

```
DO [WHILE condition | UNTIL condition]
    statements
LOOP [WHILE condition | UNTIL condition]
```

Put a condition on `DO` *or* on `LOOP`, or on neither (an endless loop). `DO` must begin a statement, either at the start of a line or after a colon.

| Form | Test | Minimum passes |
|---|---|---|
| `DO WHILE c ... LOOP` | before each pass; continues while `c` is true | 0 |
| `DO UNTIL c ... LOOP` | before each pass; continues until `c` is true | 0 |
| `DO ... LOOP WHILE c` | after each pass; repeats while `c` is true | 1 |
| `DO ... LOOP UNTIL c` | after each pass; repeats until `c` is true | 1 |
| `DO ... LOOP` | none; use `EXIT DO` to leave | — |

`EXIT DO` and its synonym `EXIT LOOP` leave the loop. Any statements after `LOOP` on the same line, or after the `LOOP WHILE/UNTIL` condition, run once the loop ends.

### Example

```basic
i = 0
DO
  i = i + 1
  IF i = 3 THEN EXIT DO
  PRINT i;
LOOP
PRINT " | after do, i ="; i
i = 0
DO WHILE i < 3
  i = i + 1
  PRINT i;
LOOP
PRINT " | pre-test WHILE"
i = 0
DO UNTIL i >= 3
  i = i + 1
  PRINT i;
LOOP
PRINT " | pre-test UNTIL"
i = 10
DO WHILE i < 3
  PRINT "never"
LOOP
PRINT "pre-test can run zero times"
i = 10
DO
  PRINT i;
  i = i + 1
LOOP WHILE i < 3
PRINT " | post-test runs at least once"
i = 0
DO
  i = i + 1
  PRINT i;
LOOP UNTIL i = 3
PRINT " | post-test UNTIL"
```

```
 1 2 | after do, i = 3
 1 2 3 | pre-test WHILE
 1 2 3 | pre-test UNTIL
pre-test can run zero times
 10 | post-test runs at least once
 1 2 3 | post-test UNTIL
```

---

## 2.9 EXIT

### Syntax

```
EXIT FOR
EXIT WHILE
EXIT DO        (or EXIT LOOP)
EXIT FUNCTION
```

### Description

| Statement | Leaves |
|---|---|
| `EXIT FOR` | the innermost `FOR ... TO`, `FOR ... IN` or `FOR EACH` loop |
| `EXIT WHILE` | the innermost `WHILE ... WEND` loop |
| `EXIT DO` / `EXIT LOOP` | the innermost `DO ... LOOP` loop |
| `EXIT FUNCTION` | the current user-defined function, returning the value assigned so far (see 2.12) |

`EXIT` can appear anywhere inside the loop body, including inside nested block IFs and single-line IFs. An `EXIT` for one kind of loop passes through any loops of other kinds that enclose it. For example, an `EXIT FOR` inside a `WHILE` that is inside a `FOR` leaves both the `WHILE` and the `FOR`.

Errors:

- `EXIT` without a keyword: `EXIT must be followed by FOR, WHILE, LOOP, DO, or FUNCTION`.
- `EXIT FOR` (or `WHILE`/`DO`) outside a matching loop: `'FOR' without matching loop structure`.
- `EXIT FUNCTION` outside a function stops the program with an empty `Runtime Error:` message.

### Example

```basic
FOR r = 1 TO 3
  c = 0
  DO
    c = c + 1
    IF c = 2 THEN EXIT DO
  LOOP
  IF r = 2 THEN
    EXIT FOR
  END IF
  PRINT "r ="; r; " c ="; c
NEXT
PRINT "stopped at r ="; r
```

```
r = 1 c = 2
stopped at r = 2
```

> **Caution:** For `FOR ... IN` and `FOR EACH` loops, end the loop with a plain `NEXT`, not `NEXT var`, if the body can run `EXIT FOR`. With `NEXT var`, the exit leaves `var` behind and it is parsed as a statement, which causes `Invalid assignment statement`. `FOR ... TO` loops do not have this problem.

---

## 2.10 Labels and GOTO

### Syntax

```
label:
label: statement
GOTO label
```

### Description

A label is an identifier directly followed by a colon. It marks the position of the next token. Label names are case-sensitive: `GOTO top` does not find `Top:`. Duplicate labels are reported when the program is loaded (`Duplicate label found`). `GOTO label` continues execution at the label. If the label does not exist, the error is `Label 'x' not found for GOTO.`

Labels are global. A label inside a function body can be reached from anywhere, but jumping into or out of a function body is not supported.

> **Warning: any `identifier :` counts as a label.** The label scanner records *every* identifier that is directly followed by a colon, even in the middle of a line. `a = b : c = b : PRINT a` creates the label `b` twice, so the program fails to load with `Duplicate label found: b`. Likewise `GOSUB s : PRINT "x"` creates a label named `s` and clashes with a real `s:` label. Avoid ending a statement with a bare variable or label name before a colon. Put the statement on its own line, or end it with something other than an identifier, such as `a = b + 0 :`.

> **Caution:** Do not `GOTO` out of a `FOR`, `WHILE` or `DO` body. The loop is still active, so execution continues from the label as if inside the loop. The program usually ends with `Expected token NEXT but got None` when the input runs out. Use `EXIT FOR`/`EXIT WHILE`/`EXIT DO` instead.

### Example

```basic
attempt = 0
Retry:
attempt = attempt + 1
PRINT "attempt"; attempt
IF attempt < 3 THEN GOTO Retry
PRINT "done"
```

```
attempt 1
attempt 2
attempt 3
done
```

---

## 2.11 GOSUB and RETURN

### Syntax

```
GOSUB label
...
label:
    statements
    RETURN
```

### Description

`GOSUB` saves the current position on a return stack and jumps to `label`. `RETURN` pops the most recent position and continues with the statement after the `GOSUB`. Subroutines can call other subroutines; the stack has no fixed depth limit.

- `RETURN` with an empty stack causes `RETURN without GOSUB.`
- If the label is missing, the error is `Label 'x' not found.`
- Subroutines share all variables with the rest of the program. There are no parameters or locals. Use `FUNCTION` (2.12) when you need them.
- Put subroutines after an `END`, or jump around them with `GOTO`, so the main flow of control does not run into them.
- A function that calls `GOSUB` but never `RETURN`s has its extra stack entries removed when the function returns.
- Keep `GOSUB label` at the end of its line, or on its own line. See the label warning in 2.10.

### Example

```basic
total = 0
amount = 40 : GOSUB AddTax
amount = 60 : GOSUB AddTax
PRINT "Total with tax:"; total
END

AddTax:
  total = total + amount * 1.05
  GOSUB LogLine
  RETURN

LogLine:
  PRINT "  added"; amount
  RETURN
```

```
  added 40
  added 60
Total with tax: 105
```

---

## 2.12 User-defined functions (FUNCTION ... END FUNCTION)

### Syntax

```
FUNCTION name([param1[, param2 ...]])
    statements
    name = return_value
    [EXIT FUNCTION]
END FUNCTION
```

Calls:

```
result = name(arg1, arg2, ...)     ' as an expression
name(arg1, arg2, ...)              ' as a statement; the return value is discarded
```

### Definition rules

- The parentheses are **required**, even with no parameters: `FUNCTION now_str$()`. If they are missing, the interpreter stops while loading the program with the message `FUNCTION 'x' requires parameter list in parentheses (use () for no params)`.
- Parameters are plain identifiers separated by commas. They have no types or defaults. A `$` suffix is part of the name, as with any variable.
- Function names are **not case-sensitive** at the call site. `area(1,2)`, `AREA(1,2)` and `Area(1,2)` all call the same function. A second definition with the same name is an error when the program is loaded: `Duplicate FUNCTION definition`.
- Definitions cannot be nested.
- A definition can appear anywhere at the top level of the program. The pre-scan registers it, so calls placed before the definition work. The main flow of control skips function bodies.
- A function name can end in `$` (for example `greet$`). Its return value then starts as `""` instead of `0`.

Definition errors (missing parentheses, duplicate or nested definitions, missing `END FUNCTION`) are raised while the program is being loaded. They print a Python traceback and exit with status 1, before any statement runs.

### Returning a value

The function's name is used as a variable inside the body. Its value when the body ends becomes the return value. It starts as `0`, or `""` for `$` names, so a function that never assigns it returns that default. `EXIT FUNCTION` returns immediately with whatever value has been assigned so far.

> **Important:** Inside the body, assign the return value using **exactly the same spelling and case** as in the `FUNCTION` line. Variable assignment matches names exactly. Given `FUNCTION Mixed(a)`, the statement `mixed = a + 1` creates a separate variable and the function returns `0`.

### Calling

- **As an expression:** `name(args)` can appear anywhere an expression is allowed, including inside other calls, in `PRINT`, and in `` `${...}` `` string interpolation.
- **As a statement:** a line that starts with `name(args)` calls the function and discards the result. This is useful for functions with side effects. Parentheses are needed even with no arguments.
- The number of arguments must equal the number of parameters. Otherwise the error is `Function 'f' expects 2 argument(s), got 1.`
- If a user function has the same name as a variable, `name(...)` always calls the function.

```basic
FUNCTION area(w, h)
  area = w * h
END FUNCTION

FUNCTION initials$(first$, last$)
  initials$ = LEFT$(first$, 1) + LEFT$(last$, 1)
END FUNCTION

FUNCTION log_msg(m$)
  PRINT "[log] "; m$
END FUNCTION

PRINT "area ="; area(3, 4)
PRINT "initials: "; initials$("Ada", "Lovelace")
log_msg("called as a statement")
r = log_msg("called as an expression")
PRINT "log_msg returned"; r
```

```
area = 12
initials: AL
[log] called as a statement
[log] called as an expression
log_msg returned 0
```

### Scope and shadowing

DbBasic functions use *shadow* scoping instead of a separate local symbol table:

1. When a function is called, the current values of any global variables with the same names as the **parameters**, the **function name**, and any names **declared with `DIM` inside the body** are saved. Name matching here is case-insensitive.
2. The parameters are bound to the argument values, and the function-name variable is set to its default.
3. When the function returns, by any route including an error, the saved values are put back. Names that did not exist before the call are deleted.

The consequences:

- Parameters and `DIM`-declared names are local in effect. `DIM a, b` declares several at once.
- **Every other variable is global.** Reading an undeclared name inside a function reads the global value. Assigning to it changes, or creates, the global variable, and the change remains after the call. The loop variable of a `FOR` inside a function is global too, unless you `DIM` it.
- Arguments are passed **by value for numbers and strings**. Arrays and hashes are passed **by reference**. Changes to their contents, such as `PUSH`, element assignment and hash keys, are visible to the caller.

```basic
FUNCTION sum_to(n)
  DIM i, acc
  acc = 0
  FOR i = 1 TO n
    acc = acc + i
  NEXT
  scratch = 99
  sum_to = acc
END FUNCTION

n = 7 : i = 100 : acc = -1
PRINT "sum_to(10) ="; sum_to(10)
PRINT "n ="; n; " i ="; i; " acc ="; acc
PRINT "scratch leaked to global ="; scratch
```

```
sum_to(10) = 55
n = 7 i = 100 acc =-1
scratch leaked to global = 99
```

### Recursion, early exit and array arguments

Functions can call themselves and each other. Each call saves and restores its own parameters and `DIM` names, so recursion is safe as long as every working variable is a parameter or declared with `DIM`.

```basic
FUNCTION fact(n)
  IF n <= 1 THEN
    fact = 1
  ELSE
    fact = n * fact(n - 1)
  END IF
END FUNCTION

FUNCTION first_neg(arr)
  DIM k
  first_neg = -1
  FOR k = 0 TO UBOUND(arr)
    IF arr(k) < 0 THEN
      first_neg = k
      EXIT FUNCTION
    END IF
  NEXT
END FUNCTION

FUNCTION add_item(arr, item$)
  PUSH arr, item$
END FUNCTION

PRINT "fact(10) ="; fact(10)
DIM v(3)
v(0) = 5 : v(1) = 2 : v(2) = -7 : v(3) = 1
PRINT "first negative at index"; first_neg(v)
DIM tags(0)
tags(0) = "a"
add_item(tags, "b")
PRINT "tags after call: "; tags
```

```
fact(10) = 3628800
first negative at index 2
tags after call: [a, b]
```

A function can return an array or hash by assigning it to the function name, for example `make_list = tmp` where `tmp` is a `DIM`-declared array.

### Where functions are available

Functions are registered from the program text before it runs, so a call can come before the definition. They are available as follows:

| Where | Functions available |
|---|---|
| Main program | its own |
| `RUN` child | its own and the caller's. A child function with the same name as one of the caller's replaces it while the child runs. When the child returns, the caller's set is restored, so the child's functions are not visible to the caller. |
| `CHAIN` target | its own only. `CHAIN` replaces the running program. |
| `EVAL` string | the caller's, plus any defined in the string. Functions defined in the string are not kept afterwards. |
| REPL | every function defined so far in the session. Type the definition over several lines; the REPL keeps reading (prompt `...>`) until `END FUNCTION`. Defining a function again replaces it. |

---

## 2.13 Functions as first-class arguments

Four constructs take the **bare name** of a function, written without parentheses, and call it for each element:

| Construct | The function is called with | Result |
|---|---|---|
| `MAP(array, fn)` | each element | new array of return values |
| `FILTER(array, fn [, flag])` | each element | new array of elements for which `fn` is true. If `flag` is `0`, the result holds the elements for which `fn` is false. |
| `REDUCE(array, fn [, initial])` | `(accumulator, element)` | final accumulator value |
| `SORT array WITH fn [ASC\|DESC]` | each element, to compute its sort key | sorts the array in place |

`fn` can be a user-defined function or a built-in function such as `UCASE$`, `LEN` or `MAX`. A name followed by `(` is evaluated as an ordinary call, not passed as a reference. Chapter 3 documents these functions in full, including the substring form of `FILTER`.

```basic
FUNCTION sq(n)
  sq = n * n
END FUNCTION
FUNCTION is_even(n)
  is_even = (MOD(n, 2) = 0)
END FUNCTION
FUNCTION add(a, b)
  add = a + b
END FUNCTION
DIM nums(4)
nums(0) = 1 : nums(1) = 2 : nums(2) = 3 : nums(3) = 4 : nums(4) = 5
PRINT MAP(nums, sq)
PRINT FILTER(nums, is_even)
PRINT REDUCE(MAP(FILTER(nums, is_even), sq), add, 0)
DIM names(2)
names(0) = "bob" : names(1) = "Alice" : names(2) = "carl"
SORT names WITH UCASE$ ASC
PRINT names
```

```
[ 1,  4,  9,  16,  25]
[ 2,  4]
 20
[Alice, bob, carl]
```

`LOAD ... TRANSFORM ... WITH fn` and `VALIDATE ... WITH fn` use the same function references. They are covered in Chapter 5.

---

## 2.14 Error handling

### Error variables

| Variable | Meaning |
|---|---|
| `ERR` | Numeric error code. `0` means no error. |
| `ERRMSG$` | Text of the most recent error. |

There is no `ERL` (error line) variable. Many statements reset `ERR` to `0` and `ERRMSG$` to `""` when they start, including every SQL statement, `RUN`, `CHAIN`, `EXECUTE` and most file statements. Read the variables straight after the statement you want to check.

Error codes used by the interpreter:

| Code | Meaning |
|---|---|
| 1 | General error. This is the default for any trapped error that did not set its own code, such as division by zero, SQL errors and bad syntax. |
| 2 | File or directory not found |
| 17 | File already exists (`NAME`) |
| 20 | Not a directory (`CHDIR`) |
| 39 | Directory not empty or other OS error (`RMDIR`) |
| 52 | Could not open a browser (`BROWSER`) |
| *n* | Any code raised with `ERROR n` |

### Soft errors and trapped errors

Errors reach a program in two ways:

1. **Soft errors.** Some statements catch their own failure, set `ERR`/`ERRMSG$`, and carry on without raising an error. `KILL` on a missing file is one example. So is any SQL error while `SET SQL_FATAL_ERRORS OFF` is in effect. Test `ERR` after these statements. `ON ERROR` is never triggered by them.
2. **Raised errors.** All other errors, such as division by zero, unknown labels, bad syntax, `ERROR n`, `NAME` on a missing file, and SQL errors while `SQL_FATAL_ERRORS` is `ON` (the default), are trapped by `ON ERROR GOTO` if a handler is active. Otherwise they stop the program.

Chapter 6 says which file statements raise errors and which set `ERR`.

### ON ERROR GOTO

```
ON ERROR GOTO label
ON ERROR GOTO 0
```

`ON ERROR GOTO label` makes `label` the error handler. The label must exist somewhere in the program. If it does not, the error is `Label 'x' not found for ON ERROR GOTO.` When a raised error occurs while a handler is active and the program is not already inside the handler, the interpreter does the following:

1. It sets `ERR`, to `1` if the failing statement left it at `0`, and sets `ERRMSG$` to the error message. Error messages raised by the interpreter itself include `at line L, col C` and a token context.
2. It remembers the statement after the one that failed as the resume point.
3. It jumps to `label`.

`ON ERROR GOTO 0` turns error trapping off.

An error that occurs **inside** the handler, before a `RESUME`, is not trapped again. It stops the program.

The handler runs in the context where the error happened. If the error happened inside a `FOR` body or inside a function, `RESUME NEXT` continues that loop or function.

### RESUME

```
RESUME NEXT
RESUME label
```

| Form | Effect |
|---|---|
| `RESUME NEXT` | Continue with the statement after the one that failed. This is the next colon-separated statement, or the next line. |
| `RESUME label` | Continue at `label`. |

Either form ends handler mode, so later errors are trapped again. A bare `RESUME`, which in classic BASIC retries the failed statement, is **not** supported and causes `Expected NEXT after RESUME.` `RESUME` used outside a handler causes `RESUME NEXT without an active error.` (or `RESUME without an active error.`). `RESUME` can appear inside block IFs within the handler.

### ERROR

```
ERROR code [, message$]
```

`ERROR` raises an error deliberately. `code` must be numeric; it is truncated to an integer and stored in `ERR`. `message$` is stored in `ERRMSG$`. Without a message, `ERRMSG$` is set to `User-defined error <code>`. If a handler is active, control goes to it. Otherwise the program stops with `Runtime Error: Error <code>: <message>`.

### Example: trapping and resuming

```basic
ON ERROR GOTO Handler
PRINT "start"
x = 10 / 0
PRINT "after divide"
ERROR 42, "custom problem"
PRINT "after ERROR 42"
NAME "no_such.txt" AS "other.txt"
PRINT "after NAME"
END

Handler:
  PRINT "  trapped ERR ="; ERR; ": "; ERRMSG$
  RESUME NEXT
```

```
start
  trapped ERR = 1: Division by zero
after divide
  trapped ERR = 42: custom problem
after ERROR 42
  trapped ERR = 2: [Errno 2] No such file or directory: 'no_such.txt' -> 'other.txt'
after NAME
```

### Example: retrying with RESUME label

```basic
attempts = 0
ON ERROR GOTO Fix
Retry:
attempts = attempts + 1
IF attempts < 3 THEN ERROR 500, "not ready"
PRINT "succeeded on attempt"; attempts
END

Fix:
  PRINT "  error"; ERR; "- retrying"
  RESUME Retry
```

```
  error 500- retrying
  error 500- retrying
succeeded on attempt 3
```

### Interaction with SET SQL_FATAL_ERRORS

`SET SQL_FATAL_ERRORS ON|OFF` (Chapter 4) decides whether a failed SQL statement is a raised error or a soft error:

- **ON** (the default): the error is raised as `Fatal DB Error: ...`. An `ON ERROR` handler traps it if one is active; otherwise the program stops.
- **OFF**: `ERR = 1` and `ERRMSG$` are set and execution continues. `ON ERROR` is not triggered.

In both modes the failing SQL is echoed to stderr in a `--- FAILED SQL ---` block.

```basic
SET SQL_FATAL_ERRORS OFF
SELECT * FROM missing_table;
IF ERR <> 0 THEN PRINT "SQL failed softly: "; ERRMSG$
SET SQL_FATAL_ERRORS ON
ON ERROR GOTO H
SELECT * FROM missing_table;
PRINT "resumed"
END
H:
  PRINT "trapped: ERR ="; ERR
  RESUME NEXT
```

stdout:

```
(0 rows returned)
SQL failed softly: no such table: missing_table
trapped: ERR = 1
resumed
```

---

## 2.15 Program control: END, RUN, CHAIN, EVAL, EXECUTE, CLEAR

### END

```
END
```

Stops the program. A bare `END` line at the top level stops the main loop. Anywhere else, for example in an `IF`, a loop, a function, a `RUN` child or an `EVAL` string, `END` exits the interpreter process immediately with status 0. Open files are not explicitly closed first.

```basic
FOR i = 1 TO 5
  IF i = 3 THEN END
  PRINT i
NEXT
PRINT "never"
```

```
 1
 2
```

### RUN

```
RUN filename$ [, arg1 [, arg2 ...]]
```

Runs another DbBasic script as a sub-program, then returns to the statement after `RUN`.

- `filename$` is a string expression; `~` is expanded. A missing file is a raised error, `RUN setup error: RUN: File not found: ...`, with `ERR = 2`.
- The arguments are converted to strings and become the child's `COMMAND$(1)`, `COMMAND$(2)`, and so on. Numbers are converted using Python's formatting, so `42` becomes `"42.0"`. Use `STR$()` or a string literal if the exact text matters.
- The child starts with a **copy** of the caller's variables. When it finishes, the caller's variables are restored from that copy, so nothing the child assigns comes back to the caller. Use files or the database to pass results back.
- The database connection and open file handles are **shared** with the caller.
- An error inside the child does not stop the caller. The caller continues with `ERR = 1` and `ERRMSG$` set to the child's error. After a successful run, `ERR = 0`.
- `END` inside the child, except a bare top-level `END` line, terminates the whole process, not just the child.
- The child can define its own `FUNCTION`s and call the caller's. Its functions are discarded when it returns (see "Where functions are available" in 2.12).

```basic
REM report.bas
PRINT "  report.bas: arg1 = "; COMMAND$(1); ", arg2 = "; COMMAND$(2)
PRINT "  report.bas sees title$ = "; title$
title$ = "changed by report.bas"
```

```basic
title$ = "Q3 Sales"
RUN "report.bas", "east", 42
PRINT "back in caller: title$ = "; title$; ", ERR ="; ERR
```

```
  report.bas: arg1 = east, arg2 = 42.0
  report.bas sees title$ = Q3 Sales
back in caller: title$ = Q3 Sales, ERR = 0
```

### CHAIN

```
CHAIN filename$ [, arg1 [, arg2 ...]] [PRESERVE]
```

Replaces the running program with another script. Control does not come back to the caller.

- All open files are closed. The current database connection is closed and a new default database is opened. Tables in an in-memory database are lost.
- The arguments become the new program's `COMMAND$(n)` values.
- Without `PRESERVE`, the new program starts with no variables. With `PRESERVE`, string and numeric variables are copied, except `ERR`, `ERRMSG$`, `SQL_ROWCOUNT`, `SQL_FOUND`, `SQL_NOTFOUND` and `RECNO`. Each array or hash `name` is serialized to JSON in a string variable named `name_JSON$`. Use `PARSEJSON` (Chapter 3) to rebuild it.
- The engine choice (`DATABASE ENGINE`), `SQL_FATAL_ERRORS`, `HASH_KEYS` mode and `TRON` state are carried over. The `ON ERROR` handler is cleared.
- `CHAIN` always prints status lines: `CHAIN: Transferred control to ...`, then, when they apply, `CHAIN: Arguments passed: ...`, `CHAIN: Variables preserved` and `CHAIN: Serialized X as X_JSON$`.
- A missing file is a raised error with `ERR = 2`.
- The chained program's `FUNCTION`s replace the caller's.

```basic
REM stage2.bas
PRINT "stage2: arg = "; COMMAND$(1); ", user$ = "; user$; ", n ="; n
PRINT "stage2: items_JSON$ = "; items_JSON$
```

```basic
user$ = "dan"
n = 3
DIM items(1)
items(0) = "x" : items(1) = "y"
CHAIN "stage2.bas", "go" PRESERVE
PRINT "this line is never reached"
```

```
CHAIN: Serialized items as items_JSON$
CHAIN: Transferred control to stage2.bas
CHAIN: Arguments passed: go
CHAIN: Variables preserved
stage2: arg = go, user$ = dan, n = 3
stage2: items_JSON$ = ["x", "y"]
```

### EVAL

```
EVAL code$
```

Runs a string of DbBasic source code. `code$` can contain several lines separated by `CHR$(10)` or by colons, including complete loops and block IFs.

- The code runs in a fresh interpreter that **shares** the caller's variables (the same variable table), open files, database connection and command-line arguments. Variables it creates or changes stay visible afterwards.
- Labels belong only to the evaluated string, so it cannot `GOTO` the caller's labels. It can call the caller's `FUNCTION`s, as well as functions defined inside the same string.
- An error inside the evaluated code is printed as `Runtime Error: ...` on stderr. It does **not** stop the caller and does **not** trigger the caller's `ON ERROR` handler.
- An empty or all-blank string does nothing. A non-string argument causes an error.

```basic
x = 5
EVAL "y = x * 2"
PRINT "y ="; y
op$ = "+"
EVAL "PRINT 10 " + op$ + " 3"
code$ = "FOR i = 1 TO 3 : PRINT i * x : NEXT"
EVAL code$
EVAL "PRINT 1 +"
PRINT "caller continues after a failed EVAL"
```

```
y = 10
 13
 5
 10
 15
Runtime Error: Unexpected token in factor: ('NEWLINE', '\n', 9) at line 1, col 10.
  Context: '+' -> ['
' (NEWLINE)] <- (end)
caller continues after a failed EVAL
```

(The `Runtime Error` lines go to stderr.)

### EXECUTE

```
EXECUTE sql$
```

Runs a **SQL** string built at run time. On SQLite, `sql$` can hold several `;`-separated statements, and the results of each `SELECT`/`WITH`/`PRAGMA` are printed in the current output format. `EXECUTE` does not run DbBasic code; use `EVAL` for that. Errors follow `SQL_FATAL_ERRORS` and are reported as `SQL execution error: ...`. Chapter 4 has the full description.

```basic
CREATE TABLE log2024 (msg TEXT);
CREATE TABLE log2025 (msg TEXT);
year$ = "2025"
EXECUTE "INSERT INTO log" + year$ + " VALUES ('hello');"
EXECUTE "SELECT COUNT(*) AS n FROM log" + year$
```

```
+---+
| n |
+---+
| 1 |
+---+
(1 rows returned)
```

### CLEAR

```
CLEAR
```

Deletes every variable, including arrays, hashes, `ERR` and `ERRMSG$`. User-defined functions, labels, open files, the database and all `SET` options are left alone. Reading a variable after `CLEAR` gives the default value, `0` or `""`.

```basic
a = 1 : b$ = "x"
CLEAR
PRINT "a ="; a; " b$ = ["; b$; "]"
```

```
a = 0 b$ = []
```

---

## 2.16 Debugging: TRON, TROFF, DUMP, SHOW VARIABLES

### TRON / TROFF

```
TRON
TROFF
```

`TRON` turns on line tracing. Before each line runs, the interpreter prints `[n]> source text`, where `n` is the line number in the program after preprocessing. `TROFF` turns tracing off. Each pass through a loop body is traced. The `NEXT`/`WEND`/`LOOP` lines that close a loop are not traced.

### SHOW VARIABLES

```
SHOW VARIABLES
```

Prints every variable in creation order, as `name (python-type): value`. Values longer than 50 characters are cut short with `...`. (`SHOW TABLES` and `SHOW INDEXES` are database commands; see Chapter 4.)

```basic
x = 1
TRON
FOR i = 1 TO 2
  x = x * 10
NEXT
TROFF
PRINT "x ="; x
SHOW VARIABLES
```

```
[3]> FOR i = 1 TO 2
[4]> x = x * 10
[4]> x = x * 10
x = 100
--- Current Variables ---
x (float): 100.0
i (float): 3.0
```

### DUMP

```
DUMP VARIABLES | LABELS | JUMPS | TOKENS
```

| Target | Output |
|---|---|
| `VARIABLES` | `=== VARIABLE DUMP ===`, then each variable in alphabetical order with its value (arrays and hashes are shown as `ARRAY[n]` or `HASH[n]`) and its type |
| `LABELS` | each label, with the token index and line and column it points to |
| `JUMPS` | the pre-computed jump map of block IFs (`elseifs`, `else`, `endif`) and `DO` loops (`loop`) |
| `TOKENS` | the token stream around the current position, with the current token marked `->` |

```
=== VARIABLE DUMP ===
  arr                  = ARRAY[3]                       (list)
  h                    = HASH[1]                        (dict)
  i                    = 3.0                            (float)
  name$                = "Ann"                          (str)
  x                    = 100.0                          (float)
=== LABEL DUMP ===
  Here                 -> Token[58] (Line 14, Col 6)
```

---

## 2.17 Running DbBasic

### Command line

```
python dbbasic.py [--debug] [--dump-tokens] program.bas [arg1 arg2 ...]
python dbbasic.py [--debug] [--dump-tokens] - [arg1 arg2 ...]
python dbbasic.py [--repl]
```

| Form | Behaviour |
|---|---|
| no arguments, or only `--repl` | Starts the interactive REPL. Combining `--repl` with any other argument does not start the REPL; `--repl` is then treated as a file name. |
| `program.bas args...` | Runs the file. All remaining words become program arguments. |
| `- args...` | Reads the program source from standard input. |
| `--debug` | Turns on internal parser debug output. It can appear anywhere on a run-a-file command line and is removed before the remaining arguments are processed. Very few code paths produce debug output. `--debug` on its own gives `Error: No source file specified.` |
| `--dump-tokens` | Prints every token (`(TYPE, value, offset)`) before the program runs. It can appear anywhere on the line. |

Before the program is tokenized, the source goes through two preprocessing steps:

1. `INCLUDE "file"` lines are replaced by the contents of the named file. The path is relative to the including file, and circular includes are skipped. This feature is currently broken; see 2.18.
2. Line continuations (a trailing `_`) are joined. This is described in Chapter 1.

If the file does not exist, the interpreter prints `Error: File 'x' not found.` If the file is empty, it prints `No source code provided.`

**Exit status.** The process exits with status 0 when the program finishes or stops at `END`. It exits with status 1 when:

- the program stops with an untrapped runtime error, including an error raised inside an `ON ERROR` handler;
- the lexer rejects the source;
- the script file is missing or unreadable;
- a `FUNCTION` definition is malformed. This error escapes as a Python exception.

An error trapped by `ON ERROR GOTO` and resumed does not affect the exit status. A failing SQL statement under `SET SQL_FATAL_ERRORS OFF` doesn't either.

### Program arguments: COMMAND$

`COMMAND$(n)` returns the *n*th program argument as a string, counting from 1. If *n* is less than 1 or greater than the number of arguments, it returns `""`. There is no argument-count function, so loop until you get an empty string. The same function returns the arguments passed by `RUN` and `CHAIN`.

```basic
i = 1
WHILE COMMAND$(i) <> ""
  PRINT i; ": "; COMMAND$(i)
  i = i + 1
WEND
```

```
$ python dbbasic.py args.bas report.csv "two words" 3
 1: report.csv
 2: two words
 3: 3
```

`ENVIRON$(name$)` and `CURDIR$` (Chapter 3) are also useful for program set-up.

### The interactive REPL

```
$ python dbbasic.py
DbBasic REPL (Type 'EXIT' to quit)
Supports single-line loops (e.g., FOR I=1 TO 5: PRINT I: NEXT)
DbBasic> x = 5
DbBasic> PRINT x * 2
 10
DbBasic> FOR I=1 TO 3: PRINT I: NEXT
 1
 2
 3
```

- Each line you type is tokenized and run on its own. Variables, the database connection, open files and `SET` options persist between lines.
- `EXIT` or `QUIT` (any case), or end-of-file (Ctrl-D, or Ctrl-Z on Windows), leaves the REPL. Ctrl-C prints `Type 'EXIT' to quit.` and continues.
- Because each line is separate, **block structures must fit on one line**. Block `IF ... END IF` cannot span several REPL lines; you get `Mismatched 'IF'`. Labels exist only within the line that defines them, so `GOTO`/`GOSUB` work only within one line.
- A `FUNCTION` definition is the exception to the one-line rule. After a line starting with `FUNCTION name`, the REPL keeps reading lines (prompt `...>`) until `END FUNCTION`. The function stays defined for the rest of the session.
- Errors are printed as `REPL Error: ...` and the session continues.

### HELP

```
HELP
HELP ALL
HELP topic [subtopic]
HELP "topic name"
```

`HELP` works in the REPL and in programs. It reads its entries from the built-in help registry.

| Form | Output |
|---|---|
| `HELP` | all topic names in three columns |
| `HELP ALL` | every topic in full |
| `HELP GOSUB`, `HELP LOAD CSV`, `HELP SHOW CREATE TABLE` | the description, syntax and examples for one topic. A second word is accepted only from a fixed list (`CSV`, `JSON`, `JSONL`, `XML`, `FIXED`, `TEXT`, `EXCEL`, `PARQUET`, `IN`, `OUTPUT`, `EMAIL`, `USING`, `ENGINE`, `OPEN`, `TABLES`, `VARIABLES`, `INDEXES`, `BROWSER`, `CREATE`, `TABLE`). |
| `HELP "FOR IN"` | a quoted topic name, needed for topics whose second word is not in that list |

If no topic matches exactly but some topics start with the name you gave, they are listed as suggestions. Otherwise `HELP` prints `No help available for 'X'. Type HELP to see list.`

The help topics related to this chapter are `IF`, `FOR`, `FOR IN`, `WHILE`, `GOSUB`, `ERROR`, `ON ERROR`, `RESUME`, `END`, `RUN`, `CHAIN`, `EXECUTE`, `EXIT`, `TRON`, `TROFF`, `SHOW VARIABLES`, `MAP`, `FILTER`, `REDUCE` and `SORT`. Several of them are inaccurate (see 2.18).

```
DbBasic> HELP GOSUB
('GOSUB', 'GOSUB', 5)

=== HELP: GOSUB ===
Description: Jumps to a subroutine at the specified label. RETURN command jumps back.
Syntax:      GOSUB label
Examples:
  GOSUB CalculateTax
========================
```

---

## 2.18 Implementation notes and discrepancies

Each of the following was confirmed by running the interpreter.

**Bugs and limitations**

1. **Nested loops** (fixed). Skipping to the end of a loop used to count every `FOR`, `WHILE` and `DO` token. As a result:
   - `FOR EACH` inside `FOR ... TO` failed with `Unexpected 'NEXT'`.
   - `DO WHILE` or `LOOP WHILE` inside `WHILE ... WEND` silently skipped the rest of the program.
   - A second `EXIT DO` or `EXIT LOOP` in a loop body jumped to the wrong place.

   Only keywords that begin a statement now open a block, and `NEXT` closes `FOR`, `FOR EACH` and `FOR ... IN` alike.
2. *(merged into item 1)*
3. *(merged into item 1)*
4. **`EXIT FOR` with `NEXT var`** (fixed). In `FOR ... IN` and `FOR EACH` loops, the variable name after `NEXT` used to be left unconsumed, which caused `Invalid assignment statement`.
5. **Labels.** Any `identifier :` sequence is recorded as a label, even mid-line, for example `a = b : ...` or `GOSUB s : ...`. Duplicates prevent the program from loading.
6. **`GOTO` out of a loop** leaves the loop active, which eventually causes `Expected token NEXT but got None`.
7. **Return value case.** The return value must be assigned with the exact case used in the `FUNCTION` line. Otherwise the function returns `0` or `""`. This happens because assignment matches names exactly while function calls do not.
8. **Functions in `RUN`/`CHAIN` targets, `EVAL` strings and the REPL** (fixed). These never registered `FUNCTION` definitions, so calls failed with `Unknown function`. Each function now records the token list it was defined in, and each of these entry points registers the new source's functions (see 2.12).
9. **`RUN` arguments** are converted with Python `str()`, so `42` arrives as `"42.0"`.
10. **`END` inside a `RUN` child or an `EVAL` string** terminates the whole process, because `END` calls `sys.exit` and is not caught.
11. **`INCLUDE`** (fixed): it used to fail for every file that existed, because its marker lines began with `'`. See [1.4.1](01-language-fundamentals.md#141-include).
12. **`RECNO` numbering is inconsistent.** In `FOR ... IN CSV` it starts at 2 even without a header row. In `JSONL` it counts blank lines. It is deleted at the end of every loop, which also hides the outer loop's `RECNO` when loops are nested.
13. **Exit status** (fixed): it was always 0, even after a runtime error; it is now 1 (see 2.17). `EXIT FUNCTION` outside a function still gives an empty `Runtime Error:` message.
14. **`HELP` prints the raw token tuple** before every entry, for example `('GOSUB', 'GOSUB', 5)`. This looks like leftover debug output.
15. `PRINT x;` immediately followed by `:` is a syntax error (`Unexpected token in factor: COLON`), so `FOR i = 1 TO 3: PRINT i;: NEXT` fails. Write `PRINT i : NEXT`, or split the line.
16. `CHAIN` always prints its `CHAIN: ...` status lines to stdout, which cannot be turned off.

**Documentation that does not match the code**

- `HELP IF` gives the example `IF x=1 THEN: PRINT 1: END IF`. It fails with `Unknown statement: COLON`.
- `HELP EXECUTE` says it "Runs a dynamic string as code" and gives `EXECUTE "PRINT 1 + 2"` and `EXECUTE "GOTO " + label$` as examples. `EXECUTE` runs **SQL** only; those examples fail with a SQL syntax error. The statement that runs DbBasic code is `EVAL`.
- `HELP RUN` says control "returns to the prompt". It actually returns to the calling program. The help also omits arguments and the fact that variables are restored afterwards.
- `HELP CHAIN` says "Variables are cleared". This is true only without `PRESERVE`, and the help does not mention `PRESERVE` or arguments.
- `HELP EXIT` describes only leaving the REPL. It does not mention `EXIT FOR/WHILE/DO/LOOP/FUNCTION`.
- `HELP RESUME` says `RESUME NEXT` resumes "at the line following the error". It actually resumes at the next *statement*, which can be later on the same line after a colon. A bare `RESUME` is not supported, although classic BASIC allows it.
- `HELP FOR IN` lists `SQL` as a keyword (`FOR var IN SQL(...)`). The actual SQL form is `FOR var IN (SELECT ...)`. The help omits `FILES`.
- `README.md` says `CLEAR` "resets all user variables (and user-defined functions)". `CLEAR` deletes only variables; functions remain callable.
- `docs/DbBasicCommandRerence.md` describes `EXIT` as applying only to loops. It also applies to `EXIT FUNCTION`.
- `examples/errorhandling.bas` uses `ERROR Number` followed by `ON ERROR GOTO 0` inside the handler, expecting the error to be re-raised and the handler turned off. Because errors inside a handler are not trapped, `ERROR Number` stops the program immediately and `ON ERROR GOTO 0` never runs.
