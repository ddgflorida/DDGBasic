REM Grid demo: BROWSE as a picker and as an editor, on a table of 10,000 rows.
REM BROWSE fetches rows a page at a time, so large tables open at once.
REM Keys: arrows, PgUp/PgDn, Home/End, Enter, Esc; the mouse and wheel work too.
REM Click a heading (or press F3) to sort by it, again to reverse; type to jump to a row.
DATABASE OPEN ":memory:"
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, city TEXT, email TEXT, phone TEXT, placed TEXT, amount REAL);
INSERT INTO orders (customer, city, email, phone, placed, amount)
    SELECT 'Customer ' || (i % 250 + 1),
           CASE i % 5 WHEN 0 THEN 'Boston' WHEN 1 THEN 'Denver' WHEN 2 THEN 'Miami' WHEN 3 THEN 'Austin' ELSE 'Seattle' END,
           'customer' || (i % 250 + 1) || '@example.com',
           '555-' || SUBSTR('000' || (i % 10000), -4),
           DATE('2026-01-01', '+' || (i % 300) || ' days'),
           ROUND((i * 731 % 100000) / 100.0, 2) - 25
    FROM (WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 10000) SELECT i FROM n);
COLOR 15, 1, 0, 3
CLS

REM 1. A picker. The customer column stays put while the others scroll (FREEZE 2 keeps
REM    id and customer), amounts are shown as money, and the row colour comes from the query:
REM    yellow for big orders, red for refunds (negative amounts).
BROWSE (SELECT id, customer, city, email, phone, placed, amount,
               CASE WHEN amount < 0 THEN 12 WHEN amount > 900 THEN 14 END AS shade
          FROM orders ORDER BY id) AT 1, 1, 22, 72 TITLE "Pick an order (click a heading to sort)" FREEZE 2 FORMAT amount "$#,##0.00" COLOR "shade" INTO picked
IF LASTKEY$ <> CHR$(27) THEN x = ALERT("You picked order " & picked.id & ";" & picked.customer & ", " & picked.city)

REM 2. An editor: Enter or typing edits a cell, Ins adds a row, Del deletes one
BROWSE (SELECT id, customer, amount FROM orders) EDIT KEY "id" TITLE "Edit orders (Esc when done)"

COLOR 7, 0
CLS
PRINT (SELECT COUNT(*) FROM orders); " orders, total "; FORMAT$((SELECT SUM(amount) FROM orders), "$#,###,##0.00")
REM EXPECT: 10000 orders, total
