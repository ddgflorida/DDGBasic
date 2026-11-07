REM ===================================================================
REM Row-by-row logic: allocating limited stock to orders.
REM
REM   Each order takes what is left after the orders before it, by priority;
REM   some customers accept part of an order, others want all or nothing.
REM   In SQL alone this needs recursive queries or window tricks. Here it is
REM   a loop over a query, plain IF rules, and bind variables, inside one
REM   transaction that is rolled back if any step fails.
REM ===================================================================
DATABASE OPEN ":memory:"
CREATE TABLE stock (sku TEXT PRIMARY KEY, on_hand INTEGER NOT NULL CHECK (on_hand >= 0));
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, sku TEXT, qty INTEGER,
                     priority INTEGER, partial_ok INTEGER);
CREATE TABLE allocations (order_id INTEGER, sku TEXT, qty INTEGER, outcome TEXT);

INSERT INTO stock VALUES ('WIDGET', 100), ('GADGET', 30), ('GIZMO', 12);
INSERT INTO orders (customer, sku, qty, priority, partial_ok) VALUES
    ('Acme Corp', 'WIDGET', 60, 1, 0),
    ('Globex',    'WIDGET', 50, 2, 1),
    ('Initech',   'WIDGET', 20, 3, 0),
    ('Hooli',     'GADGET', 20, 1, 0),
    ('Umbrella',  'GADGET', 25, 2, 1),
    ('Stark Ltd', 'GIZMO',   5, 1, 1),
    ('Wayne Co',  'GADGET', 10, 3, 1);

title$ = "Allocating stock by priority"
PRINT title$
PRINT REPEAT$("-", LEN(title$))

ON ERROR GOTO undo_allocation
BEGIN TRANSACTION;
FOR o IN (SELECT id, customer, sku, qty, partial_ok FROM orders ORDER BY sku, priority, id)
    available = (SELECT on_hand FROM stock WHERE sku = :o.sku)
    IF available >= o.qty THEN
        take = o.qty : outcome$ = "shipped in full"
    ELSEIF available > 0 AND o.partial_ok THEN
        take = available : outcome$ = "part shipped, " & (o.qty - available) & " back-ordered"
    ELSE
        take = 0
        IF o.partial_ok THEN outcome$ = "back-ordered (none left)" ELSE outcome$ = "held: wants all or nothing"
    END IF
    IF take > 0 THEN UPDATE stock SET on_hand = on_hand - :take WHERE sku = :o.sku;
    INSERT INTO allocations VALUES (:o.id, :o.sku, :take, :outcome$);
    PRINT PADRIGHT$(o.customer, 10, " ") & " " & PADRIGHT$(o.sku, 7, " ") & " wants " & _
          PADLEFT$(o.qty, 3, " ") & ", gets " & PADLEFT$(take, 3, " ") & ": " & outcome$
NEXT
COMMIT;
allocation_done:
ON ERROR GOTO 0
REM EXPECT: Acme Corp  WIDGET  wants  60, gets  60: shipped in full
REM EXPECT: Globex     WIDGET  wants  50, gets  40: part shipped, 10 back-ordered
REM EXPECT: Initech    WIDGET  wants  20, gets   0: held: wants all or nothing

PRINT
PRINT "Stock left:"
SELECT sku, on_hand FROM stock ORDER BY sku;

REM --- A failure part way through rolls everything back --------------------------
REM A manual correction tries to take 40 more widgets than are left. The CHECK
REM constraint refuses it; the handler rolls back the whole batch, including the
REM change made before it.
PRINT
PRINT "A correction batch that fails part way:"
before = (SELECT SUM(on_hand) FROM stock)
ON ERROR GOTO undo_correction
BEGIN TRANSACTION;
UPDATE stock SET on_hand = on_hand + 5 WHERE sku = 'GADGET';
UPDATE stock SET on_hand = on_hand - 40 WHERE sku = 'WIDGET';
COMMIT;
correction_done:
ON ERROR GOTO 0
after = (SELECT SUM(on_hand) FROM stock)
IF after = before THEN PRINT "  stock unchanged (" & after & " units): the batch was rolled back"
REM EXPECT: the batch was rolled back
END

REM Error handlers: undo the whole transaction, then carry on after it
FUNCTION reason$(message$)
    REM The database's words, without where in the program it happened
    reason$ = message$
    at = INSTR(message$, " at line ")
    IF at > 0 THEN reason$ = LEFT$(message$, at - 1)
    reason$ = REPLACE$(reason$, "Fatal DB Error: ", "")
END FUNCTION

undo_allocation:
    PRINT "  allocation failed, nothing changed: " & reason$(ERRMSG$)
    ROLLBACK;
    RESUME allocation_done

undo_correction:
    PRINT "  refused: " & reason$(ERRMSG$)
    ROLLBACK;
    RESUME correction_done
