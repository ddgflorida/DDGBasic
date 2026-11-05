REM EDIT RECORD on SQLite and DuckDB: UPDATE, a refused change, INSERT for a missing row,
REM and Esc. Keys come from the test runner. Failed checks raise errors.
DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"
CREATE TABLE contacts (id INTEGER PRIMARY KEY, last_name TEXT NOT NULL, email TEXT, credit REAL CHECK (credit >= 0));
INSERT INTO contacts VALUES (1, 'smith', 'a@x.com', 100);
id = 1
REM Keys: Ctrl-Y "jones" Tab Tab Ctrl-Y "-5" Enter (CHECK refuses it), a key, then Tab Tab Ctrl-Y "50" Enter
EDIT RECORD (SELECT * FROM contacts WHERE id = :id) TITLE "Contact" INTO rec
REM EXPECT: CHECK constraint failed
IF rec.last_name <> "jones" OR rec.credit <> 50 THEN ERROR 1, "SQLITE: INTO record"
IF (SELECT last_name || '/' || credit FROM contacts WHERE id = 1) <> "jones/50.0" THEN ERROR 1, "SQLITE: UPDATE"
id = 99
REM No row: a blank form that INSERTs. Keys: Tab (id left for SQLite to number) Ctrl-Y "brown" Tab "b@x.com" Tab "7" Enter
EDIT RECORD (SELECT * FROM contacts WHERE id = :id) INTO added
IF (SELECT COUNT(*) FROM contacts WHERE last_name = 'brown' AND email = 'b@x.com' AND credit = 7) <> 1 THEN ERROR 1, "SQLITE: INSERT"
REM Esc changes nothing. Keys: Ctrl-Y "zzz" Esc
id = 1
EDIT RECORD (SELECT id, last_name FROM contacts WHERE id = :id)
IF (SELECT last_name FROM contacts WHERE id = 1) <> "jones" THEN ERROR 1, "SQLITE: Esc"
IF LASTKEY$ <> CHR$(27) THEN ERROR 1, "SQLITE: LASTKEY$ after Esc"
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"
CREATE TABLE contacts (id INTEGER PRIMARY KEY, last_name TEXT NOT NULL, email TEXT, credit REAL CHECK (credit >= 0));
INSERT INTO contacts VALUES (1, 'smith', 'a@x.com', 100);
id = 1
REM Keys: Ctrl-Y "jones" Tab Tab Ctrl-Y "-5" Enter (CHECK refuses it), a key, then Tab Tab Ctrl-Y "50" Enter
EDIT RECORD (SELECT * FROM contacts WHERE id = :id) TITLE "Contact" INTO rec
REM EXPECT: CHECK constraint failed
IF rec.last_name <> "jones" OR rec.credit <> 50 THEN ERROR 1, "DUCKDB: INTO record"
IF (SELECT last_name || '/' || credit FROM contacts WHERE id = 1) <> "jones/50.0" THEN ERROR 1, "DUCKDB: UPDATE"
id = 99
REM No row: a blank form that INSERTs. Keys: "2" Tab (DuckDB needs the id typed) Ctrl-Y "brown" Tab "b@x.com" Tab "7" Enter
EDIT RECORD (SELECT * FROM contacts WHERE id = :id) INTO added
IF (SELECT COUNT(*) FROM contacts WHERE last_name = 'brown' AND email = 'b@x.com' AND credit = 7) <> 1 THEN ERROR 1, "DUCKDB: INSERT"
REM Esc changes nothing. Keys: Ctrl-Y "zzz" Esc
id = 1
EDIT RECORD (SELECT id, last_name FROM contacts WHERE id = :id)
IF (SELECT last_name FROM contacts WHERE id = 1) <> "jones" THEN ERROR 1, "DUCKDB: Esc"
IF LASTKEY$ <> CHR$(27) THEN ERROR 1, "DUCKDB: LASTKEY$ after Esc"
COLOR 7, 0
CLS
PRINT "edit_record: all checks passed"
REM EXPECT: edit_record: all checks passed
