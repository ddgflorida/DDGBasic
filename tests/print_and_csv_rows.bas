REM PRINT followed by : or ELSE, CSV rows with too few or too many fields, and
REM cleanup after a failed CREATE TABLE load. Failed checks raise errors.
DATABASE OPEN ":memory:"
FOR i = 1 TO 3: PRINT i;: NEXT
PRINT
REM EXPECT: 1 2 3
PRINT: PRINT "after blank"
x = 2
IF x = 1 THEN PRINT "yes"; ELSE PRINT "no";
PRINT " <- same line"
REM EXPECT: no <- same line

LOAD CSV "data/short_rows.csv" CREATE TABLE s OPTIONS "header=true"
REM EXPECT: Warning: line 3 has 2 fields, expected 3; the missing fields are loaded as NULL.
REM EXPECT: the extra fields are ignored.
IF (SELECT COUNT(*) FROM s) <> 3 THEN ERROR 1, "short row not loaded"
IF (SELECT COUNT(*) FROM s WHERE a = '4' AND c IS NULL) <> 1 THEN ERROR 1, "short row not padded with NULL"

FUNCTION not_a_hash(r)
    not_a_hash = 1
END FUNCTION
ON ERROR GOTO failed
LOAD CSV "data/short_rows.csv" CREATE TABLE s2 OPTIONS "header=true" TRANSFORM ROW WITH not_a_hash
ERROR 1, "the load should have failed"
failed:
ON ERROR GOTO 0
IF (SELECT COUNT(*) FROM sqlite_master WHERE name = 's2') <> 0 THEN ERROR 1, "failed CREATE TABLE load left a table"
PRINT "print_and_csv_rows: all checks passed"
REM EXPECT: print_and_csv_rows: all checks passed
