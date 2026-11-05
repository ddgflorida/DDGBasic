REM Mouse support: INKEY$ click and wheel keys with MOUSEROW/MOUSECOL, and clicks in READ
REM (fields and buttons), MENU, ALERT, MENUBAR$, BROWSE and EDIT TEXT. The test runner sends
REM SGR mouse reports (ESC [ < button ; col ; row M). Failed checks raise errors.
DATABASE OPEN ":memory:"
CREATE TABLE t (id INTEGER, name TEXT); INSERT INTO t VALUES (1, 'a'), (2, 'b'), (3, 'c');
COLOR 15, 1 : CLS

REM 1. A click (its release is skipped), then a wheel turn
k$ = INKEY$(0)
IF k$ <> "CLICK" OR MOUSEROW <> 5 OR MOUSECOL <> 10 THEN ERROR 1, "INKEY$ click: " & k$ & STR$(MOUSEROW) & STR$(MOUSECOL)
k$ = INKEY$(0)
IF k$ <> "WHEELDOWN" THEN ERROR 1, "wheel: " & k$

REM 2. READ: click the Qty field, type 7, click Save
name$ = "ann" : qty = 1
@ 3, 5 SAY "Name: " GET name$ PICTURE "@S10"
@ 4, 5 SAY "Qty : " GET qty
@ 6, 5 BUTTON "Save"
@ 6, 15 BUTTON "Cancel" CANCEL
READ
IF BUTTON$ <> "Save" OR qty <> 7 OR name$ <> "ann" THEN ERROR 1, "READ clicks: " & BUTTON$ & STR$(qty)

REM 3. MENU at 10, 20: click the second item
item = MENU(10, 20, "Add", "Edit", "Quit")
IF item <> 2 THEN ERROR 1, "MENU click: " & STR$(item)

REM 4. ALERT: click the No button
IF ALERT("Quit?", "Yes", "No") <> 2 THEN ERROR 1, "ALERT click"

REM 5. MENUBAR$: click the Edit title, then its second item
c$ = MENUBAR$("File:Open|Quit", "Edit:Cut|Copy|Paste")
IF c$ <> "Edit.Copy" THEN ERROR 1, "MENUBAR$ clicks: " & c$

REM 6. BROWSE: click the second row, then click it again to choose it
BROWSE (SELECT id, name FROM t ORDER BY id) AT 1, 1, 10, 40 INTO r
IF r.id <> 2 THEN ERROR 1, "BROWSE clicks: " & STR$(r.id)

REM 7. EDIT TEXT: click after "one", type "!", save
memo$ = "one" + CHR$(10) + "two"
EDIT TEXT memo$ AT 3, 5, 12, 50
IF memo$ <> "one!" + CHR$(10) + "two" THEN ERROR 1, "EDIT TEXT click: " & memo$

COLOR 7, 0
CLS
PRINT "mouse: all checks passed"
REM EXPECT: mouse: all checks passed
