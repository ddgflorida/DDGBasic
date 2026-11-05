REM SET OUTPUT FILE ... APPEND, SET OUTPUT OFF running queries, FILES RECURSIVE filtering
REM folders by the pattern, and quoted OPTIONS values. Failed checks raise errors.
DATABASE OPEN ":memory:"
CREATE TABLE t (id INTEGER, name TEXT); INSERT INTO t VALUES (1, 'a'), (2, 'b');
SET OUTPUT FILE "append_out.csv" APPEND FORMAT CSV
SELECT * FROM t WHERE id = 1;
SELECT * FROM t WHERE id = 2;
SET OUTPUT FILE "over_out.csv" FORMAT CSV
SELECT * FROM t WHERE id = 1;
SELECT * FROM t WHERE id = 2;
SET OUTPUT CONSOLE
READ FILE "append_out.csv" INTO a$
IF INSTR(a$, "1,a") = 0 OR INSTR(a$, "2,b") = 0 THEN ERROR 1, "APPEND should keep both results"
IF INSTR(MID$(a$, 2), "id,name") > 0 THEN ERROR 1, "APPEND should write one CSV header"
READ FILE "over_out.csv" INTO o$
IF INSTR(o$, "1,a") > 0 OR INSTR(o$, "2,b") = 0 THEN ERROR 1, "FILE without APPEND replaces the file"
ON ERROR GOTO json_refused
SET OUTPUT FILE "x.json" APPEND FORMAT JSON
ERROR 1, "APPEND with JSON should be refused"
json_refused:
IF INSTR(ERRMSG$, "APPEND can't be used with FORMAT JSON") = 0 THEN ERROR 1, "message: " & ERRMSG$
RESUME after_json
after_json:
ON ERROR GOTO 0
SET OUTPUT CONSOLE

SET SQL_FATAL_ERRORS OFF
SET OUTPUT OFF
SELECT * FROM no_such_table;
IF ERR <> 1 THEN ERROR 1, "SET OUTPUT OFF should still run the query (ERR)"
SET OUTPUT CONSOLE
SET SQL_FATAL_ERRORS ON

DIM found AS ARRAY
FILES "data/tree/*.txt" INTO found RECURSIVE
names$ = ""
FOR i = 0 TO UBOUND(found)
    names$ = names$ & BASENAME$(found(i)) & " "
NEXT
IF names$ <> "a.txt b.txt d.txt " THEN ERROR 1, "FILES RECURSIVE: " & names$
n = 0
FOR f$ IN FILES("data/tree/*.txt" RECURSIVE)
    n = n + 1
NEXT
IF n <> 3 THEN ERROR 1, "FOR ... IN FILES should agree with FILES"

REM A quoted value may contain commas, semicolons and word= text
FOR rec IN CSV "data/semi.csv" OPTIONS "skip=1, delimiter=';', header=true"
    got$ = rec.name
    EXIT FOR
NEXT
IF got$ <> "A" THEN ERROR 1, "quoted delimiter option"
ANALYZE CSV "data/dates.csv" INTO rep OPTIONS "header=true, constraints=""[mixed]:REGEX(^d=\d$)"""
f = rep("CONSTRAINT_FAILURES")
IF UBOUND(f) <> 2 THEN ERROR 1, "the REGEX constraint should fail on all 3 rows"
IF f(0).FAILED_RULE <> "REGEX(^d=\d$)" THEN ERROR 1, "the d= inside the quoted value was taken for a key: " & f(0).FAILED_RULE
PRINT "output_and_options: all checks passed"
REM EXPECT: output_and_options: all checks passed
