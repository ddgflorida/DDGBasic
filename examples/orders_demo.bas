REM Orders demo: a master-detail screen. The orders are on top; the lines of the order
REM under the bar are shown below and follow it as it moves. Enter (or Tab) goes to the
REM lines, where Enter edits a cell, Ins adds a line (its order_id is filled in) and Del
REM deletes one; F6 or Esc goes back to the orders. Esc on the orders ends.
DATABASE OPEN ":memory:"
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, placed TEXT, status TEXT);
CREATE TABLE order_lines (line_id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id),
                          product TEXT, qty INTEGER, price REAL);
INSERT INTO orders VALUES (1, 'Acme Corp', '2026-01-05', 'shipped'), (2, 'Globex', '2026-01-09', 'open'),
    (3, 'Initech', '2026-02-01', 'open'), (4, 'Hooli', '2026-02-11', 'cancelled');
INSERT INTO order_lines (order_id, product, qty, price) VALUES
    (1, 'Widget', 10, 2.5), (1, 'Gadget', 1, 99.95), (2, 'Gizmo', 3, 12), (3, 'Widget', 100, 2.25),
    (3, 'Sprocket', 7, 4), (3, 'Flange', 12, 1.1), (4, 'Gadget', 2, 99.95);

COLOR 15, 1, 0, 3
CLS
BROWSE (SELECT o.id, o.customer, o.placed, o.status,
               (SELECT SUM(qty * price) FROM order_lines WHERE order_id = o.id) AS amount,
               CASE o.status WHEN 'cancelled' THEN 7 WHEN 'open' THEN 14 END AS shade
          FROM orders o ORDER BY o.id) INTO o TITLE "Orders" _
    FORMAT amount "#,##0.00" COLOR "shade" _
    DETAIL (SELECT line_id, product, qty, price, qty * price AS total
              FROM order_lines WHERE order_id = :o.id ORDER BY line_id) _
    EDIT KEY "line_id" TITLE "Lines" FORMAT price "#,##0.00", total "#,##0.00"

COLOR 7, 0
CLS
IF HASH_COUNT(o) = 0 THEN
    PRINT "There are no orders."
ELSE
    PRINT "Last order:"; o.id; " for "; o.customer; ":"; (SELECT COUNT(*) FROM order_lines WHERE order_id = :o.id); " lines, total "; TRIM$(FORMAT$((SELECT SUM(qty * price) FROM order_lines WHERE order_id = :o.id), "$#,##0.00"))
END IF
REM EXPECT: Last order: 3 for Initech: 4 lines, total $54.45
