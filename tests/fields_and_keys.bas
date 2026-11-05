REM ON KEY hot keys, and the new entry fields: @D dates, calculator-style numeric masks,
REM @Z, @R, @K, CHECKBOX and LIST. Keys come from the test runner. Failed checks raise errors.
FUNCTION show_help()
    BOX 10, 10, 14, 60, "Help" DOUBLE
    @ 12, 12 SAY "Help text. Press a key."
    k$ = INKEY$(0)
    helps = helps + 1
END FUNCTION
FUNCTION stamp()
    stamped$ = "yes"
END FUNCTION
helps = 0 : stamped$ = ""
COLOR 15, 1 : CLS
ON KEY "F1" CALL show_help
ON KEY "CTRL-T" CALL stamp

d$ = "" : amount = 1234.5 : qty = 0 : phone$ = "" : active = 0 : flag$ = "N" : state$ = "FL" : name$ = "old"
@ 2, 5 SAY "Date  : " GET d$ PICTURE "@D"
@ 3, 5 SAY "Amount: " GET amount PICTURE "99,999.99"
@ 4, 5 SAY "Qty   : " GET qty PICTURE "@Z 9999"
@ 5, 5 SAY "Phone : " GET phone$ PICTURE "@R (999) 999-9999"
@ 6, 5 SAY "Active: " GET active CHECKBOX
@ 7, 5 SAY "Flag  : " GET flag$ CHECKBOX
@ 8, 5 SAY "State : " GET state$ LIST "CA,FL,NY,TX"
@ 9, 5 SAY "Name  : " GET name$ PICTURE "@K"
REM Keys: date 2024-02-30 (refused) then 2024-02-29; F1 (help; a key); amount 7.25; qty 12;
REM       phone 5551234567; Space (check); Y (check); "n" (jumps to NY) Space "t" (list: TX);
REM       Ctrl-T; name "new" (the first key clears "old"); Enter
READ
REM EXPECT: Not a valid date
IF d$ <> "2024-02-29" THEN ERROR 1, "date: " & d$
IF amount <> 7.25 THEN ERROR 1, "calculator amount: " & STR$(amount)
IF qty <> 12 THEN ERROR 1, "@Z qty: " & STR$(qty)
IF phone$ <> "5551234567" THEN ERROR 1, "@R phone: " & phone$
IF active <> -1 THEN ERROR 1, "checkbox: " & STR$(active)
IF flag$ <> "Y" THEN ERROR 1, "text checkbox: " & flag$
IF state$ <> "TX" THEN ERROR 1, "list: " & state$
IF name$ <> "new" THEN ERROR 1, "@K name: " & name$
IF helps <> 1 OR stamped$ <> "yes" THEN ERROR 1, "ON KEY handlers"

REM The screen is put back after a handler. Keys: F1, a key
before$ = SAVESCREEN()
k$ = INKEY$(1)
IF SAVESCREEN() <> before$ THEN ERROR 1, "the screen after a hot key"
REM With the binding off, F1 is an ordinary key. Keys: F1
ON KEY "F1" OFF
k$ = INKEY$(0)
IF k$ <> "F1" THEN ERROR 1, "ON KEY OFF: " & k$

REM A list from a query, opened and chosen with the keys. Keys: Space Down Enter Enter
DATABASE OPEN ":memory:"
CREATE TABLE c (name TEXT); INSERT INTO c VALUES ('Blue'), ('Green'), ('Red');
colour$ = ""
@ 12, 5 SAY "Colour: " GET colour$ LIST (SELECT name FROM c ORDER BY name)
READ
IF colour$ <> "Green" THEN ERROR 1, "LIST from a query: " & colour$
COLOR 7, 0
CLS
PRINT "fields_and_keys: all checks passed"
REM EXPECT: fields_and_keys: all checks passed
