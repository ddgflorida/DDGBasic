REM Semicolons inside SQL string literals, quoted identifiers and comments
REM must not end the statement. Any failed check raises an error (exit 1).
DATABASE OPEN ":memory:"
CREATE TABLE t (id INTEGER, note TEXT);
INSERT INTO t VALUES (1, 'a;b');
INSERT INTO t VALUES (2, 'it''s; fine');
INSERT INTO t VALUES (3, 'x') -- trailing; comment
;
INSERT INTO t /* block; comment */ VALUES (4, 'y');
INSERT INTO t
  VALUES (5, 'multi;
line');
EXECUTE "INSERT INTO t VALUES (6, 'e;f'); INSERT INTO t VALUES (7, 'g')"

n = (SELECT COUNT(*) FROM t)
IF n <> 7 THEN ERROR 1, "expected 7 rows, got " + STR$(n)

n = (SELECT COUNT(*) FROM t WHERE note LIKE '%;%')
IF n <> 4 THEN ERROR 1, "expected 4 notes containing ;, got " + STR$(n)

note$ = (SELECT note FROM t WHERE id = 2)
IF note$ <> "it's; fine" THEN ERROR 1, "escaped quote lost: " + note$

FOR r IN (SELECT "id" AS "semi;col" FROM t WHERE id = 1)
  IF r("SEMI;COL") <> 1 THEN ERROR 1, "quoted identifier with ; failed"
NEXT

DATABASE ENGINE DUCKDB
CREATE TABLE d (s VARCHAR);
INSERT INTO d VALUES ('duck;db'), ('x');
n = (SELECT COUNT(*) FROM d WHERE s LIKE '%;%')
IF n <> 1 THEN ERROR 1, "DuckDB: expected 1 row, got " + STR$(n)

PRINT "sql_semicolons: all checks passed"
