REM SQL wherever a statement can start: after THEN and ELSE, after ':', after a label,
REM and after another SQL statement's ';'. Failed checks raise errors.
DATABASE OPEN ":memory:"
CREATE TABLE t (id INTEGER, name TEXT); INSERT INTO t VALUES (1, 'a');
ok = 1
IF ok THEN INSERT INTO t VALUES (2, 'b');
IF ok = 0 THEN INSERT INTO t VALUES (99, 'wrong'); ELSE INSERT INTO t VALUES (3, 'c');
x = 5 : INSERT INTO t VALUES (4, 'd'); : PRINT "after colon"
REM EXPECT: after colon
retry: UPDATE t SET name = 'A' WHERE id = 1;
FOR i = 1 TO 2: INSERT INTO t VALUES (10 + :i, 'loop'); : NEXT
DELETE FROM t WHERE id = 4; DELETE FROM t WHERE id = 12;
IF ok THEN SELECT 'inline' AS v;
REM EXPECT: inline
s$ = "x: SELECT ;"
IF s$ <> "x: SELECT " + ";" THEN ERROR 1, "a string with ':' and SELECT"
IF (SELECT COUNT(*) FROM t) <> 4 THEN ERROR 1, "row count " & STR$((SELECT COUNT(*) FROM t))
IF (SELECT name FROM t WHERE id = 1) <> "A" THEN ERROR 1, "UPDATE after a label"
IF (SELECT COUNT(*) FROM t WHERE id = 99) <> 0 THEN ERROR 1, "THEN branch ran when false"
IF (SELECT COUNT(*) FROM t WHERE id IN (2, 3, 11)) <> 3 THEN ERROR 1, "THEN / ELSE / FOR rows"
PRINT "sql_anywhere: all checks passed"
REM EXPECT: sql_anywhere: all checks passed
