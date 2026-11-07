REM Values crossing between the databases and BASIC: DuckDB DECIMAL and DATE,
REM h.name$ keys, nested bind variables, and failed queries with SQL_FATAL_ERRORS OFF

REM 1. DuckDB DECIMAL arrives as a number, DATE and TIMESTAMP as ISO text
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"
CREATE TABLE t (amt DECIMAL(10,2), d DATE, ts TIMESTAMP);
INSERT INTO t VALUES (1.25, DATE '2024-01-03', TIMESTAMP '2024-01-03 10:11:12');
x = (SELECT SUM(amt) FROM t)
IF TYPENAME$(x) <> "FLOAT" OR x * 2 <> 2.5 THEN ERROR 1, "1a: " & TYPENAME$(x)
FOR r IN (SELECT amt, d, ts FROM t)
    IF TYPENAME$(r.amt) <> "FLOAT" THEN ERROR 1, "1b: " & TYPENAME$(r.amt)
    IF r.d <> "2024-01-03" OR r.ts <> "2024-01-03 10:11:12" THEN ERROR 1, "1c: " & r.d & "|" & r.ts
    j$ = JSON_SERIALIZE$(r)
NEXT
IF INSTR(j$, """AMT"": 1.25") = 0 OR INSTR(j$, """D"": ""2024-01-03""") = 0 THEN ERROR 1, "1d: " & j$
IF 1.25 IN (SELECT amt FROM t) THEN ok = 1 ELSE ERROR 1, "1e"
DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"

REM 2. h.name$ reads the key it wrote, and finds a "name" field from a query or JSON
DIM h AS HASH
h.name$ = "Ann"
IF h.name$ <> "Ann" THEN ERROR 1, "2a: [" & h.name$ & "]"
h("city$") = "Rome"
IF h.city$ <> "Rome" THEN ERROR 1, "2b"
p = PARSEJSON("{""title"": ""T""}")
IF p.title$ <> "T" THEN ERROR 1, "2c"
p.title$ = "U"
IF JSON_SERIALIZE$(p) <> "{""title"": ""U""}" THEN ERROR 1, "2d: " & JSON_SERIALIZE$(p)
IF (SELECT :h.name$ || '!') <> "Ann!" THEN ERROR 1, "2e"

REM 3. Bind variables reach nested hash fields
n.a.b = 5
IF (SELECT :n.a.b * 2) <> 10 THEN ERROR 1, "3"

REM 4. A failed query with SQL_FATAL_ERRORS OFF sets ERR and the program goes on
SET SQL_FATAL_ERRORS OFF
v = (SELECT nosuch FROM nowhere)
IF ERR = 0 OR v <> "" THEN ERROR 1, "4a"
IF 3 IN (SELECT nosuch FROM nowhere) THEN ERROR 1, "4b"
REPORT (SELECT nosuch FROM nowhere) TITLE "never shown"
IF ERR = 0 THEN ERROR 1, "4c"
SET SQL_FATAL_ERRORS ON

PRINT "data_values: all checks passed"
REM EXPECT: data_values: all checks passed
