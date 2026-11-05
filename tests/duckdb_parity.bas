REM DuckDB parity: SQL helper functions, SHOW INDEXES, EXECUTE results, JSON output
REM of dates/decimals. Failed checks raise errors; printed output is checked by EXPECT.
REM EXPECT: CREATE INDEX idx_t_id ON t(id);
REM EXPECT: ALTER TABLE u ADD PRIMARY KEY (k);
REM EXPECT: | from_execute |
DATABASE ENGINE DUCKDB
s$ = (SELECT STUFF('Hello World', 7, 5, 'There'))
IF s$ <> "Hello There" THEN ERROR 1, "STUFF: " + s$
IF (SELECT INSTR('banana', 'an', 3)) <> 4 THEN ERROR 1, "INSTR with 3 arguments"
IF (SELECT INSTR('banana', 'an', 1, 2)) <> 4 THEN ERROR 1, "INSTR with 4 arguments"
IF (SELECT INSTR('banana', 'an')) <> 2 THEN ERROR 1, "built-in INSTR with 2 arguments"
IF (SELECT INITCAP('hello world')) <> "Hello World" THEN ERROR 1, "INITCAP"
IF (SELECT SOUNDEX('Tymczak')) <> "T522" THEN ERROR 1, "SOUNDEX"
IF (SELECT LEFT$('abcdef', 3) || RIGHT$('abcdef', 2) || REPLICATE('x', 2)) <> "abcefxx" THEN ERROR 1, "LEFT$/RIGHT$/REPLICATE"
IF (SELECT CHARINDEX('lo', 'Hello')) <> 4 THEN ERROR 1, "CHARINDEX"

CREATE TABLE t (id INTEGER, d DATE, amt DECIMAL(10,2));
INSERT INTO t VALUES (1, DATE '2024-07-04', 12.50);
CREATE INDEX idx_t_id ON t (id);
CREATE TABLE u (k INTEGER PRIMARY KEY);
SHOW INDEXES ON t
SHOW INDEXES FROM u
EXECUTE "SELECT 1 AS from_execute"

SET OUTPUT FILE "duck_json.out" FORMAT JSON
SELECT d, amt FROM t;
SET OUTPUT CONSOLE
READ FILE "duck_json.out" INTO j$
r = PARSEJSON(j$)
IF r(0).d <> "2024-07-04" OR r(0).amt <> 12.5 THEN ERROR 1, "JSON output of DATE/DECIMAL: " + j$
PRINT "duckdb_parity: all checks passed"
