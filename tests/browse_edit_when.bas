REM BROWSE ... EDIT WHEN condition MESSAGE text$: rows can be changed only while the condition
REM holds; otherwise editing, Ins and Del are refused with the message. Keys from the test runner.
CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT);
CREATE TABLE lines (line_id INTEGER PRIMARY KEY, order_id INTEGER, qty INTEGER);
INSERT INTO orders VALUES (1, 'shipped'), (2, 'open');
INSERT INTO lines VALUES (1, 1, 5), (2, 2, 5);
REM Keys: Enter (lines of shipped order 1) Right "9" Enter, Del "y", Ins (all refused) Esc (back)
REM       Down Enter (lines of open order 2) Right "9" Enter (saved) Esc Esc
BROWSE (SELECT id, status FROM orders ORDER BY id) INTO o _
    DETAIL (SELECT line_id, qty FROM lines WHERE order_id = :o.id) _
    EDIT KEY "line_id" WHEN o.status = "open" MESSAGE "Only open orders can be changed" TITLE "Lines"
REM EXPECT: Only open orders can be changed
IF (SELECT qty FROM lines WHERE line_id = 1) <> 5 THEN ERROR 1, "the shipped order's line was changed"
IF (SELECT COUNT(*) FROM lines) <> 2 THEN ERROR 1, "a line was added or deleted"
IF (SELECT qty FROM lines WHERE line_id = 2) <> 9 THEN ERROR 1, "the open order's line should be saved"
REM A plain BROWSE: the condition is checked as the grid opens. Keys: "7" Enter (refused) Esc
locked = -1
BROWSE (SELECT line_id, qty FROM lines) EDIT KEY "line_id" WHEN NOT locked
REM EXPECT: These rows can't be changed.
IF (SELECT qty FROM lines WHERE line_id = 1) <> 5 THEN ERROR 1, "a locked grid was changed"
CLS
PRINT "browse_edit_when: all checks passed"
REM EXPECT: browse_edit_when: all checks passed
