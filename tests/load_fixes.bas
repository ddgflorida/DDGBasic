REM LOAD fixes: .xlsx and HTML with header=false, nested Parquet column names, and
REM SET NULL_HANDLING on the USING SCHEMA and normalize paths. Failed checks raise errors.
DATABASE OPEN ":memory:"
LOAD EXCEL "data/nohead.xlsx" CREATE TABLE x OPTIONS "header=false"
IF (SELECT COUNT(*) FROM x WHERE C1 = 'b' AND C2 = '2') <> 1 THEN ERROR 1, ".xlsx header=false"

LOAD HTML "data/ragged.html" CREATE TABLE h OPTIONS "header=false"
IF (SELECT COUNT(*) FROM h) <> 2 THEN ERROR 1, "HTML header=false row count"
IF (SELECT COUNT(*) FROM h WHERE C1 = 'b' AND C2 IS NULL) <> 1 THEN ERROR 1, "HTML short row not padded"

LOAD PARQUET "data/nested.parquet" CREATE TABLE p
t$ = (SELECT tags FROM p WHERE id = '1')
IF t$ <> "[""x"", ""y""]" THEN ERROR 1, "Parquet list column: " + t$

LOAD CSV "data/schema_cols.csv" CREATE TABLE s USING SCHEMA "data/schema_cols.json"
IF (SELECT SUM(amount IS NULL) + SUM(name IS NULL) FROM s) <> 2 THEN ERROR 1, "USING SCHEMA empty fields not NULL"

LOAD JSON "data/normalize.json" CREATE TABLE n OPTIONS "normalize=true"
IF (SELECT SUM(name IS NULL) + SUM(note IS NULL) FROM n) <> 2 THEN ERROR 1, "normalize empty fields not NULL"
PRINT "load_fixes: all checks passed"
