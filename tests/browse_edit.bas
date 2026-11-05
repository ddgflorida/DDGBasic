REM BROWSE ... EDIT on SQLite and DuckDB: in-place cell editing, constraint errors,
REM the locked KEY column, and NULL for an emptied number. Keys come from the test runner.
DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"
CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, qty INTEGER CHECK (qty >= 0), price REAL);
INSERT INTO items VALUES (1, 'apple', 3, 1.25), (2, 'banana', 5, 0.5);
REM Keys: Right Enter Ctrl-Y "Apricot" Enter (name) / Right "7" Enter (qty) / "-1" Enter (CHECK fails)
REM       Down Right Enter Ctrl-Y Enter (price -> NULL) / Left Left "Banana2" Tab / Esc
BROWSE "items" EDIT AT 1, 1, 12, 60 TITLE "Items"
REM EXPECT: CHECK constraint failed
REM Keys: Enter on the key column (refused) / Right "Cherry" Enter / Esc
BROWSE (SELECT id, name FROM items ORDER BY id) EDIT KEY "id" AT 1, 1, 12, 60
REM EXPECT: id is the key and cannot be changed.
IF (SELECT name FROM items WHERE id = 1) <> "Cherry" THEN ERROR 1, "SQLITE: name of row 1"
IF (SELECT qty FROM items WHERE id = 1) <> 7 THEN ERROR 1, "SQLITE: qty of row 1"
IF (SELECT name FROM items WHERE id = 2) <> "Banana2" THEN ERROR 1, "SQLITE: name of row 2"
IF (SELECT COUNT(*) FROM items WHERE id = 2 AND price IS NULL AND qty = 5) <> 1 THEN ERROR 1, "SQLITE: row 2 price/qty"
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"
CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, qty INTEGER CHECK (qty >= 0), price REAL);
INSERT INTO items VALUES (1, 'apple', 3, 1.25), (2, 'banana', 5, 0.5);
REM Keys: Right Enter Ctrl-Y "Apricot" Enter (name) / Right "7" Enter (qty) / "-1" Enter (CHECK fails)
REM       Down Right Enter Ctrl-Y Enter (price -> NULL) / Left Left "Banana2" Tab / Esc
BROWSE "items" EDIT AT 1, 1, 12, 60 TITLE "Items"
REM EXPECT: CHECK constraint failed
REM Keys: Enter on the key column (refused) / Right "Cherry" Enter / Esc
BROWSE (SELECT id, name FROM items ORDER BY id) EDIT KEY "id" AT 1, 1, 12, 60
REM EXPECT: id is the key and cannot be changed.
IF (SELECT name FROM items WHERE id = 1) <> "Cherry" THEN ERROR 1, "DUCKDB: name of row 1"
IF (SELECT qty FROM items WHERE id = 1) <> 7 THEN ERROR 1, "DUCKDB: qty of row 1"
IF (SELECT name FROM items WHERE id = 2) <> "Banana2" THEN ERROR 1, "DUCKDB: name of row 2"
IF (SELECT COUNT(*) FROM items WHERE id = 2 AND price IS NULL AND qty = 5) <> 1 THEN ERROR 1, "DUCKDB: row 2 price/qty"
COLOR 7, 0
CLS
PRINT "browse_edit: all checks passed"
REM EXPECT: browse_edit: all checks passed
