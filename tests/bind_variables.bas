REM :name is a bind variable only in SQL code. DuckDB casts (x::TYPE), list
REM slices, and colons inside literals, quoted identifiers and comments are not.
REM Any failed check raises an error (exit 1).
DATABASE ENGINE DUCKDB
v = 21
n = (SELECT '42'::INTEGER + 1)
IF n <> 43 THEN ERROR 1, "cast gave " + STR$(n)
n = (SELECT (:v)::INTEGER * 2)
IF n <> 42 THEN ERROR 1, "bind variable next to a cast gave " + STR$(n)
s$ = (SELECT 'a:b c:memory: x')
IF s$ <> "a:b c:memory: x" THEN ERROR 1, "literal with colons gave [" + s$ + "]"
n = (SELECT "col:x" FROM (SELECT 7 AS "col:x"))
IF n <> 7 THEN ERROR 1, "quoted identifier with a colon failed"
n = (SELECT len([1, 2, 3, 4][2:3]))
IF n <> 2 THEN ERROR 1, "list slice gave " + STR$(n)
SELECT 1 AS one; -- a comment with :nope in it

DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"
ATTACH ':memory:' AS aux;
n = (SELECT :v + 1)
IF n <> 22 THEN ERROR 1, "SQLite bind variable gave " + STR$(n)
PRINT "bind_variables: all checks passed"
