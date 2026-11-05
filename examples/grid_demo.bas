REM Grid demo: BROWSE as a picker and as an editor, on a table of 10,000 rows.
REM BROWSE fetches rows a page at a time, so large tables open at once.
REM Keys: arrows, PgUp/PgDn, Home/End, Enter, Esc; the mouse and wheel work too.
DATABASE OPEN ":memory:"
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, amount REAL);
INSERT INTO orders (customer, amount)
    SELECT 'Customer ' || (i % 250 + 1), ROUND(i * 7.31 % 1000, 2)
    FROM (WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 10000) SELECT i FROM n);
COLOR 15, 1, 0, 3
CLS

REM 1. A picker: Enter (or a second click) chooses a row
BROWSE (SELECT id, customer, amount FROM orders ORDER BY id) TITLE "Pick an order" INTO picked
IF LASTKEY$ <> CHR$(27) THEN x = ALERT("You picked order " & picked.id & ";" & picked.customer)

REM 2. An editor: Enter or typing edits a cell, Ins adds a row, Del deletes one
BROWSE "orders" EDIT TITLE "Edit orders (Esc when done)"

COLOR 7, 0
CLS
PRINT (SELECT COUNT(*) FROM orders); " orders, total "; FORMAT$((SELECT SUM(amount) FROM orders), "$#,###,##0.00")
REM EXPECT: 10000 orders, total
