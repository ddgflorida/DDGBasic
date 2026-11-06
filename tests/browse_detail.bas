REM BROWSE ... DETAIL on SQLite and DuckDB: the detail grid follows the master's bar, Tab
REM switches grids, a detail cell is edited, Ins adds a line linked to the master row, a
REM computed column can't be edited, Enter on the master opens its lines, and Esc on the
REM master ends with the row its bar is on. Keys from the test runner.
DATABASE ENGINE SQLITE
DATABASE OPEN ":memory:"
GOSUB checks
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"
GOSUB checks
COLOR 7, 0
CLS
PRINT "browse_detail: all checks passed"
REM EXPECT: total is worked out by the query and cannot be changed.
REM EXPECT: browse_detail: all checks passed
END

checks:
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT);
CREATE TABLE lines (line_id INTEGER PRIMARY KEY, order_id INTEGER, product TEXT, qty INTEGER, price DOUBLE);
INSERT INTO orders VALUES (1, 'Acme'), (2, 'Globex'), (3, 'Initech');
INSERT INTO lines VALUES (1, 1, 'Widget', 10, 2.5), (2, 1, 'Gadget', 1, 99.95), (3, 2, 'Gizmo', 3, 12), (4, 3, 'Widget', 100, 2.25);
REM Keys: Down Down (Initech) Tab (to the lines) Right Right "5" Enter (qty of Widget -> 5)
REM       Right Right Enter (total: refused) Ins "9" Tab "Bolt" Tab "4" Tab "0.5" Enter (a new line)
REM       Esc (back to the orders) Up Esc (done, on Globex)
BROWSE (SELECT id, customer FROM orders ORDER BY id) INTO o TITLE "Orders" _
    DETAIL (SELECT line_id, product, qty, price, qty * price AS total FROM lines WHERE order_id = :o.id ORDER BY line_id) _
    EDIT KEY "line_id" TITLE "Lines" FORMAT total "#,##0.00"
IF o.id <> 2 OR o.customer <> "Globex" THEN ERROR 1, "Esc on the master should return Globex"
IF (SELECT qty FROM lines WHERE line_id = 4) <> 5 THEN ERROR 1, "the detail edit"
IF (SELECT COUNT(*) FROM lines WHERE line_id = 9 AND order_id = 3 AND product = 'Bolt' AND qty = 4) <> 1 THEN ERROR 1, "the new line, linked to order 3"
IF (SELECT COUNT(*) FROM lines) <> 5 THEN ERROR 1, "line count"
REM Keys: Down Enter (to the lines of Globex) Esc (back) Up Tab (lines of Acme) Tab (back) Esc (done)
BROWSE (SELECT id, customer FROM orders ORDER BY id) INTO o DETAIL (SELECT product FROM lines WHERE order_id = :o.id)
IF o.id <> 1 THEN ERROR 1, "Enter should open the lines, not end: expected Acme, got " & STR$(o.id)
IF LASTKEY$ <> CHR$(27) THEN ERROR 1, "LASTKEY$ should be Esc"
REM Keys: Esc -> a master with no rows gives an empty hash
DELETE FROM orders;
BROWSE (SELECT id, customer FROM orders) INTO o DETAIL (SELECT product FROM lines WHERE order_id = :o.id)
IF HASH_COUNT(o) <> 0 THEN ERROR 1, "no rows: an empty hash"
RETURN
