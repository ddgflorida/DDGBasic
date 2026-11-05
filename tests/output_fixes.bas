REM Output fixes: whole-number bind values, FORMAT TABLE, HTML full=false, Excel titles,
REM a trailing comma in PRINT, PRINT USING mask reuse and masks with no values.
REM Failed checks raise errors; printed output is checked by EXPECT.
REM EXPECT: trailing comma	next
REM EXPECT:   1  2  3
REM EXPECT: Totals:
DATABASE OPEN ":memory:"
i = 1
CREATE TABLE t (a INTEGER, s TEXT);
INSERT INTO t VALUES (:i, :i);
IF (SELECT s FROM t) <> "1" THEN ERROR 1, "whole number bound as " + (SELECT s FROM t)
IF (SELECT typeof(:i)) <> "integer" THEN ERROR 1, "bind type"

SET OUTPUT FORMAT TABLE
SET OUTPUT FILE "out_fixes.html" FORMAT HTML OPTIONS "full=false"
SELECT * FROM t;
READ FILE "out_fixes.html" INTO h$
IF INSTR(h$, "<html") THEN ERROR 1, "full=false still wrote a full page"
SET OUTPUT FILE "out_fixes.xlsx" FORMAT EXCEL OPTIONS "title=T, subtitle=S, footer=F"
SELECT * FROM t;
SET OUTPUT CONSOLE
IF FILESIZE("out_fixes.xlsx") <= 0 THEN ERROR 1, "Excel with title/subtitle/footer was not written"

PRINT "trailing comma",
PRINT "next"
PRINT USING "###"; 1, 2, 3
PRINT USING "Totals:"
PRINT "output_fixes: all checks passed"
