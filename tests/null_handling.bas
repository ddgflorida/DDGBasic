REM LOAD stores empty or all-space fields as NULL by default; SET NULL_HANDLING
REM can keep them as text, globally or per column. Any failed check raises an error.
DATABASE OPEN ":memory:"
LOAD CSV "data/people_blanks.csv" CREATE TABLE p1 OPTIONS "header=true"
n = (SELECT COUNT(middle) FROM p1)
IF n <> 1 THEN ERROR 1, "default: COUNT(middle) = " + STR$(n)
n = (SELECT AVG(salary) FROM p1)
IF n <> 55500 THEN ERROR 1, "default: AVG(salary) = " + STR$(n)

SET NULL_HANDLING FOR "middle" TO EMPTY
LOAD CSV "data/people_blanks.csv" CREATE TABLE p2 OPTIONS "header=true"
n = (SELECT SUM(middle IS NULL) FROM p2)
IF n <> 0 THEN ERROR 1, "column rule EMPTY: middle NULLs = " + STR$(n)
n = (SELECT SUM(salary IS NULL) FROM p2)
IF n <> 1 THEN ERROR 1, "column rule: salary NULLs = " + STR$(n)

SET NULL_HANDLING TO EMPTY
SET NULL_HANDLING FOR "p3.salary" TO NULL
LOAD CSV "data/people_blanks.csv" CREATE TABLE p3 OPTIONS "header=true"
n = (SELECT SUM(salary IS NULL) FROM p3)
IF n <> 1 THEN ERROR 1, "table.column rule beats global: salary NULLs = " + STR$(n)
n = (SELECT SUM(first IS NULL) FROM p3)
IF n <> 0 THEN ERROR 1, "global EMPTY"

REM DuckDB can load empty fields into a typed column once they are NULL.
SET NULL_HANDLING TO NULL
DATABASE ENGINE DUCKDB
CREATE TABLE d (id INTEGER, first VARCHAR, middle VARCHAR, salary INTEGER);
LOAD CSV "data/people_blanks.csv" INTO TABLE d APPEND OPTIONS "header=true"
n = (SELECT COUNT(*) FROM d WHERE salary IS NULL)
IF n <> 1 THEN ERROR 1, "DuckDB typed load"
PRINT "null_handling: all checks passed"
