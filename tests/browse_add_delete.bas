REM BROWSE ... EDIT: Ins adds a row with a form, Del deletes the current row after a Y/N
REM question, on SQLite and DuckDB. Keys come from the test runner. Failed checks raise errors.
DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"
CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, qty INTEGER);
INSERT INTO items VALUES (1, 'apple', 3), (2, 'banana', 5);
REM Keys: Ins, Tab (SQLite numbers the row) "pear" Tab "4" Enter (new row; the cursor moves to it)
REM       Right Enter Ctrl-Y "Pear2" Enter (edits the new row) / Up Del "n" (kept) / Del "y" (banana deleted)
REM       Ins Esc (cancelled) / Ins Tab Tab "1" Enter (NOT NULL refused), a key, Esc / Esc
BROWSE "items" EDIT AT 1, 1, 12, 60
REM EXPECT: NOT NULL constraint failed
IF (SELECT COUNT(*) FROM items) <> 2 THEN ERROR 1, "SQLITE: row count"
IF (SELECT name FROM items WHERE id = 1) <> "apple" THEN ERROR 1, "SQLITE: apple kept"
IF (SELECT COUNT(*) FROM items WHERE id = 3 AND name = 'Pear2' AND qty = 4) <> 1 THEN ERROR 1, "SQLITE: inserted and edited row"
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"
CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, qty INTEGER);
INSERT INTO items VALUES (1, 'apple', 3), (2, 'banana', 5);
REM Keys: Ins, "3" Tab (DuckDB needs the id typed) "pear" Tab "4" Enter (new row; the cursor moves to it)
REM       Right Enter Ctrl-Y "Pear2" Enter (edits the new row) / Up Del "n" (kept) / Del "y" (banana deleted)
REM       Ins Esc (cancelled) / Ins Tab Tab "1" Enter (NOT NULL refused), a key, Esc / Esc
BROWSE "items" EDIT AT 1, 1, 12, 60
REM EXPECT: NOT NULL constraint failed
IF (SELECT COUNT(*) FROM items) <> 2 THEN ERROR 1, "DUCKDB: row count"
IF (SELECT name FROM items WHERE id = 1) <> "apple" THEN ERROR 1, "DUCKDB: apple kept"
IF (SELECT COUNT(*) FROM items WHERE id = 3 AND name = 'Pear2' AND qty = 4) <> 1 THEN ERROR 1, "DUCKDB: inserted and edited row"
COLOR 7, 0
CLS
PRINT "browse_add_delete: all checks passed"
REM EXPECT: browse_add_delete: all checks passed
