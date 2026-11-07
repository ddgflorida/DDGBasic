REM Edge cases where BASIC and SQL meet: LOAD transactions, UPSERT keys, a failed
REM DATABASE OPEN, words in SQL that look like joined keywords, comments, BLOBs

OPEN "edge_up.csv" FOR OUTPUT AS #1
PRINT #1, "id,name"
PRINT #1, "2,Bobby"
PRINT #1, "4,Dee"
CLOSE #1
OPEN "edge_dup.csv" FOR OUTPUT AS #1
PRINT #1, "id,name"
PRINT #1, "5,Five"
PRINT #1, "1,Dup"
CLOSE #1

REM 1. DuckDB: UPSERT on an INTEGER key, and a failed LOAD leaves no rows behind
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"
CREATE TABLE p (id INTEGER PRIMARY KEY, name VARCHAR);
INSERT INTO p VALUES (1, 'A'), (2, 'B');
LOAD CSV "edge_up.csv" INTO TABLE p UPSERT USING KEY "id" OPTIONS "header=true"
IF (SELECT string_agg(name, ',' ORDER BY id) FROM p) <> "A,Bobby,Dee" THEN ERROR 1, "1a"
ON ERROR GOTO load_failed
LOAD CSV "edge_dup.csv" INTO TABLE p APPEND OPTIONS "header=true"
after_duck:
ON ERROR GOTO 0
IF (SELECT COUNT(*) FROM p) <> 3 THEN ERROR 1, "1b: " & (SELECT COUNT(*) FROM p)

REM 2. SQLite: LOAD inside the program's transaction is part of it
DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"
CREATE TABLE q (id TEXT, name TEXT);
BEGIN;
LOAD CSV "edge_up.csv" INTO TABLE q APPEND OPTIONS "header=true"
LOAD CSV "edge_up.csv" INTO TABLE q UPSERT USING KEY "id" OPTIONS "header=true"
ROLLBACK;
IF (SELECT COUNT(*) FROM q) <> 0 THEN ERROR 1, "2"

REM 3. A database that cannot be opened leaves the open one in use
CREATE TABLE keep (v);
ON ERROR GOTO open_failed
DATABASE OPEN "/no/such/folder/x.db"
ON ERROR GOTO 0
INSERT INTO keep VALUES (1);
IF (SELECT COUNT(*) FROM keep) <> 1 THEN ERROR 1, "3"

REM 4. SQL text is sent as written: readfile and endif are column names here
x = (SELECT 1 AS readfile)
FOR r IN (SELECT 2 AS endif, 3 AS readfile)
    IF r("ENDIF") <> 2 OR r("READFILE") <> 3 THEN ERROR 1, "4"
NEXT

REM 5. Quotes and brackets inside /* */ comments
CREATE TABLE c (a);
INSERT INTO c VALUES (1) /* it's */;
INSERT INTO c VALUES (2) /* " */;
IF (SELECT COUNT(*) /* ) */ FROM c) <> 2 THEN ERROR 1, "5a"
IF (SELECT "a)b" FROM (SELECT 1 AS "a)b")) <> 1 THEN ERROR 1, "5b"

REM 6. FORMAT SQL writes a BLOB as a hex literal; Parquet stores a mixed column as text
CREATE TABLE b (id INTEGER, data BLOB);
INSERT INTO b VALUES (1, x'00FF');
SET OUTPUT FILE "edge_b.sql" FORMAT SQL
SELECT * FROM b;
CREATE TABLE m (v);
INSERT INTO m VALUES (1), ('a');
SET OUTPUT FILE "edge_m.parquet" FORMAT PARQUET
SELECT * FROM m;
SET OUTPUT CONSOLE
READ FILE "edge_b.sql" INTO sql$
IF INSTR(sql$, "X'00FF'") = 0 THEN ERROR 1, "6a: " & sql$
DATABASE ENGINE DUCKDB
IF (SELECT string_agg(v, ',') FROM 'edge_m.parquet') <> "1,a" THEN ERROR 1, "6b"

PRINT "sql_edges: all checks passed"
REM EXPECT: sql_edges: all checks passed
END

load_failed:
    RESUME after_duck
open_failed:
    RESUME NEXT
