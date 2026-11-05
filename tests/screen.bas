REM Text screen statements: CLS, COLOR, BOX, @ SAY/GET with PICTURE and VALID, READ,
REM MENU, BROWSE, SAVESCREEN/RESTSCREEN, INKEY$ and LASTKEY$. Keys come from the test runner's STDIN.
REM Failed checks raise errors.
DATABASE OPEN ":memory:"
CREATE TABLE customers (id INTEGER, name TEXT, credit REAL);
INSERT INTO customers VALUES (1, 'ACME', 1000), (2, 'GLOBEX', 250.5), (3, 'INITECH', 0);

COLOR 15, 1
CLS
BOX 2, 5, 9, 60, "Customer" DOUBLE
name$ = ""
phone$ = ""
credit = 0
@ 4, 8 SAY "Name  : " GET name$ PICTURE "@!S20"
@ 5, 8 SAY "Phone : " GET phone$ PICTURE "(999) 999-9999"
@ 6, 8 SAY "Credit: " GET credit VALID credit >= 0
REM Keys: "ann smith" Tab "5551234567" Tab "-5" Enter (rejected by VALID), Ctrl-Y "12" Enter
READ
COLOR 7, 0
IF name$ <> "ANN SMITH" THEN ERROR 1, "GET with @! picture: " & name$
IF phone$ <> "(555) 123-4567" THEN ERROR 1, "GET with template picture: " & phone$
IF credit <> 12 THEN ERROR 1, "numeric GET with VALID: " & STR$(credit)
IF LASTKEY$ <> CHR$(13) THEN ERROR 1, "LASTKEY$ after READ"

REM Esc puts back the values the variables had when READ started
@ 10, 8 SAY "Name  : " GET name$
REM Keys: "zzz" Esc
READ
IF name$ <> "ANN SMITH" THEN ERROR 1, "Esc should restore the value: " & name$
IF LASTKEY$ <> CHR$(27) THEN ERROR 1, "LASTKEY$ after Esc"

REM MENU and BROWSE put back what they covered, so the screen is the same afterwards
before$ = SAVESCREEN()
REM Keys: Down Enter -> item 2; then "q" picks Quit by its first letter
item = MENU(12, 8, "Save", "Delete", "Quit")
IF SAVESCREEN() <> before$ THEN ERROR 1, "MENU did not restore the screen"
IF item <> 2 THEN ERROR 1, "MENU with arrow keys: " & STR$(item)
items = SPLIT("Save,Delete,Quit", ",")
item = MENU(12, 8, items)
IF item <> 3 THEN ERROR 1, "MENU hot key: " & STR$(item)

REM Keys: Down Down Enter -> the third row
BROWSE (SELECT id, name, credit FROM customers ORDER BY id) AT 1, 1, 10, 50 TITLE "Pick" INTO row
IF row.name <> "INITECH" THEN ERROR 1, "BROWSE INTO: " & row.name
IF SAVESCREEN() <> before$ THEN ERROR 1, "BROWSE did not restore the screen"

REM SAVESCREEN of an area, overwritten and put back
part$ = SAVESCREEN(4, 8, 4, 30)
@ 4, 8 SAY "XXXXXXXXXXXXXXXXXXXXXXX"
IF SAVESCREEN() = before$ THEN ERROR 1, "SAY should have changed the screen"
RESTSCREEN part$
IF SAVESCREEN() <> before$ THEN ERROR 1, "RESTSCREEN of an area"
CLS
RESTSCREEN before$
IF SAVESCREEN() <> before$ THEN ERROR 1, "RESTSCREEN of the whole screen"

REM Keys: "k"
k$ = INKEY$
IF k$ <> "k" THEN ERROR 1, "INKEY$: [" & k$ & "]"

@ 20, 1 SAY 1234.5 PICTURE "#,###.##"
REM EXPECT: 1,234.50
LOCATE 22, 1
PRINT "screen: all checks passed"
REM EXPECT: screen: all checks passed
