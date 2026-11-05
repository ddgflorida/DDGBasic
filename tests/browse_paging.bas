REM BROWSE on more rows than one page (500): End, PgDn, EDIT and Del past the first page,
REM on SQLite and DuckDB. Keys come from the test runner. Failed checks raise errors.
DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"
CREATE TABLE big (id INTEGER PRIMARY KEY, name TEXT);
INSERT INTO big SELECT i, 'row ' || i FROM (WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 1234) SELECT i FROM n);
REM Keys: End Enter -> the last row (beyond the first 500-row page)
BROWSE (SELECT id, name FROM big ORDER BY id) AT 1, 1, 20, 60 INTO r
IF r.id <> 1234 THEN ERROR 1, "SQLITE: End should reach row 1234, got " & STR$(r.id)
REM EXPECT: 1234 of 1234
REM Keys: PgDn x 40 (past the first page), Enter
BROWSE (SELECT id, name FROM big ORDER BY id DESC) AT 1, 1, 20, 60 INTO r
IF r.id <> 1234 - 15 * 40 THEN ERROR 1, "SQLITE: PgDn x 40 in DESC order, got " & STR$(r.id)
REM Edit a cell on a later page, delete a row there, then leave. Keys: End Right Enter Ctrl-Y "last" Enter / Up Del y / Esc
BROWSE (SELECT id, name FROM big ORDER BY id) EDIT KEY "id" AT 1, 1, 20, 60
IF (SELECT name FROM big WHERE id = 1234) <> "last" THEN ERROR 1, "SQLITE: edit on a later page"
IF (SELECT COUNT(*) FROM big WHERE id = 1233) <> 0 THEN ERROR 1, "SQLITE: delete on a later page"
REM A query with its own LIMIT is loaded whole. Keys: End Enter
BROWSE (SELECT id FROM big ORDER BY id LIMIT 3) AT 1, 1, 10, 40 INTO r
IF r.id <> 3 THEN ERROR 1, "SQLITE: query with LIMIT"
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"
CREATE TABLE big (id INTEGER PRIMARY KEY, name TEXT);
INSERT INTO big SELECT i, 'row ' || i FROM (WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 1234) SELECT i FROM n);
REM Keys: End Enter -> the last row (beyond the first 500-row page)
BROWSE (SELECT id, name FROM big ORDER BY id) AT 1, 1, 20, 60 INTO r
IF r.id <> 1234 THEN ERROR 1, "DUCKDB: End should reach row 1234, got " & STR$(r.id)
REM EXPECT: 1234 of 1234
REM Keys: PgDn x 40 (past the first page), Enter
BROWSE (SELECT id, name FROM big ORDER BY id DESC) AT 1, 1, 20, 60 INTO r
IF r.id <> 1234 - 15 * 40 THEN ERROR 1, "DUCKDB: PgDn x 40 in DESC order, got " & STR$(r.id)
REM Edit a cell on a later page, delete a row there, then leave. Keys: End Right Enter Ctrl-Y "last" Enter / Up Del y / Esc
BROWSE (SELECT id, name FROM big ORDER BY id) EDIT KEY "id" AT 1, 1, 20, 60
IF (SELECT name FROM big WHERE id = 1234) <> "last" THEN ERROR 1, "DUCKDB: edit on a later page"
IF (SELECT COUNT(*) FROM big WHERE id = 1233) <> 0 THEN ERROR 1, "DUCKDB: delete on a later page"
REM A query with its own LIMIT is loaded whole. Keys: End Enter
BROWSE (SELECT id FROM big ORDER BY id LIMIT 3) AT 1, 1, 10, 40 INTO r
IF r.id <> 3 THEN ERROR 1, "DUCKDB: query with LIMIT"
COLOR 7, 0
CLS
PRINT "browse_paging: all checks passed"
REM EXPECT: browse_paging: all checks passed
