REM Editing a BROWSE cell: Enter starts with the cursor after the value, and Right
REM stops at the end of it. Keys come from the test runner's STDIN.
DATABASE OPEN ":memory:"
CREATE TABLE t (name TEXT);
INSERT INTO t VALUES ('ab');
REM Keys: Enter "c" Enter (appends: abc), Enter Right Right "d" Enter (no gap: abcd), Esc
BROWSE "t" EDIT
v$ = (SELECT name FROM t)
IF v$ <> "abcd" THEN ERROR 1, "cell edit: [" & v$ & "]"
COLOR 7, 0
CLS
PRINT "browse_cursor: all checks passed"
REM EXPECT: browse_cursor: all checks passed
