REM BROWSE sorting (F3), type-ahead, FREEZE, FORMAT and COLOR, on SQLite and DuckDB,
REM including a binary search on a sorted, paged grid. Keys come from the test runner.
DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"
CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT, city TEXT, balance REAL);
INSERT INTO people VALUES (1, 'carol', 'Boston', 10), (2, 'Alice', 'Austin', -5), (3, 'bob', NULL, 200), (4, 'dave', 'Denver', 0);
CREATE TABLE big (id INTEGER PRIMARY KEY, code TEXT);
INSERT INTO big SELECT i, 'c' || CAST(((i * 37) % 1500) + 10000 AS TEXT) FROM (WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 1500) SELECT i FROM n);
GOSUB checks
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"
CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT, city TEXT, balance DOUBLE);
INSERT INTO people VALUES (1, 'carol', 'Boston', 10), (2, 'Alice', 'Austin', -5), (3, 'bob', NULL, 200), (4, 'dave', 'Denver', 0);
CREATE TABLE big (id INTEGER PRIMARY KEY, code TEXT);
INSERT INTO big SELECT i, 'c' || CAST(((i * 37) % 1500) + 10000 AS VARCHAR) FROM range(1, 1501) t(i);
GOSUB checks
COLOR 7, 0
CLS
PRINT "browse_power: all checks passed"
REM EXPECT: browse_power: all checks passed
END

checks:
REM Keys: F3 (sort by id), F3 (reversed) Enter -> id 4
BROWSE (SELECT id, name FROM people) AT 1, 1, 12, 60 INTO r
IF r.id <> 4 THEN ERROR 1, "F3 F3 should sort by id descending, got " & STR$(r.id)
REM Keys: Right (scroll to name) F3 (sort by name, ignoring case) "c" Enter -> carol
BROWSE (SELECT id, name FROM people) AT 1, 1, 12, 60 INTO r
IF r.name <> "carol" THEN ERROR 1, "type-ahead on the sorted name should find carol, got " & r.name
REM Keys: "b" Enter -> bob (unsorted: the first column is searched)
BROWSE (SELECT name, city FROM people ORDER BY id) AT 1, 1, 12, 60 INTO r
IF r.name <> "bob" THEN ERROR 1, "type-ahead should find bob, got " & r.name
REM Keys: "a" Backspace "d" Enter -> dave; FREEZE, FORMAT and COLOR are accepted
BROWSE (SELECT name, city, balance, CASE WHEN balance < 0 THEN 4 END AS shade FROM people ORDER BY id) AT 1, 1, 12, 40 FREEZE 1 FORMAT balance "#,##0.00" COLOR "shade" INTO r
IF r.name <> "dave" THEN ERROR 1, "Backspace in type-ahead, got " & r.name
IF r.balance <> 0 THEN ERROR 1, "FORMAT changes only what is shown"
REM Keys: Right F3 (sort the paged grid by code) "c11234" Enter -> a binary search
BROWSE (SELECT id, code FROM big) AT 1, 1, 20, 60 INTO r
IF r.code <> "c11234" THEN ERROR 1, "binary search on the sorted paged grid, got " & r.code
REM Keys: Right F3 "c1123" Enter -> a search on a query with a bind variable
minid = 2
BROWSE (SELECT id, code FROM big WHERE id >= :minid) AT 1, 1, 20, 60 INTO r
IF LEFT$(r.code, 5) <> "c1123" THEN ERROR 1, "search with a bind variable, got " & r.code
REM Keys: Right F3 F3 (EDIT: name descending, dave first) Enter Ctrl-Y "Zed" Enter Esc
BROWSE "people" EDIT AT 1, 1, 12, 60
IF (SELECT name FROM people WHERE id = 4) <> "Zed" THEN ERROR 1, "sorted EDIT should rename dave"
REM Keys: Ins "9" Tab "Eve" Enter Esc -> the new-row form has no field for the COLOR column
BROWSE (SELECT id, name, CASE WHEN id > 5 THEN 14 END AS shade FROM people) EDIT KEY "id" COLOR "shade"
IF (SELECT name FROM people WHERE id = 9) <> "Eve" THEN ERROR 1, "Ins with a COLOR column"
DELETE FROM people WHERE id = 9;
RETURN
