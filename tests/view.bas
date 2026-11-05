REM VIEW: the read-only text viewer for a file, a query and a string. Keys come from the
REM test runner. Failed checks raise errors.
DATABASE OPEN ":memory:"
CREATE TABLE t (id INTEGER, name TEXT); INSERT INTO t VALUES (1, 'alpha'), (2, 'beta');
COLOR 15, 1 : CLS
before$ = SAVESCREEN()
REM Keys: PgDn "/total" Enter "n" End Esc
VIEW FILE "data/report.txt" AT 2, 2, 12, 60
REM EXPECT: Line 057 of the report  TOTAL
REM EXPECT: 57-65 of 100
IF SAVESCREEN() <> before$ THEN ERROR 1, "VIEW did not restore the screen"
IF LASTKEY$ <> CHR$(27) THEN ERROR 1, "LASTKEY$ after Esc"
REM Keys: "q"
VIEW (SELECT * FROM t ORDER BY id) TITLE "Table t"
REM EXPECT: (2 rows returned)
IF LASTKEY$ <> "q" THEN ERROR 1, "q closes the viewer"
REM Keys: Esc / Esc (a variable called file)
s$ = "one" + CHR$(10) + "two"
VIEW s$ AT 2, 2, 8, 40 TITLE "String"
file = 5
VIEW file AT 2, 2, 8, 40
ON ERROR GOTO missing
VIEW FILE "no/such/file.txt"
ERROR 1, "a missing file should be an error"
missing:
IF ERR <> 2 THEN ERROR 1, "ERR for a missing file: " & STR$(ERR)
RESUME done
done:
ON ERROR GOTO 0
COLOR 7, 0
CLS
PRINT "view: all checks passed"
REM EXPECT: view: all checks passed
