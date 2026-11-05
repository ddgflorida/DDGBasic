REM GET into hash fields, nested hash fields and array elements; Esc puts their values
REM back. Keys come from the test runner. Failed checks raise errors.
DATABASE OPEN ":memory:"
CREATE TABLE contacts (id INTEGER PRIMARY KEY, last_name TEXT, email TEXT, credit REAL);
INSERT INTO contacts VALUES (1, 'smith', 'a@x.com', 100);
id = 1
FOR rec IN (SELECT * FROM contacts WHERE id = :id)
    CLS
    @ 5, 13 SAY "Last   : " GET rec.last_name PICTURE "@!S20"
    @ 6, 13 SAY "Email  : " GET rec.email     PICTURE "@S40"
    @ 7, 13 SAY "Credit : " GET rec.credit    VALID rec.credit <= 500
    REM Keys: Ctrl-Y "jones" Tab Tab "900" Enter (refused by VALID) Ctrl-Y "250" Enter
    READ
    IF LASTKEY$ <> CHR$(27) THEN
        UPDATE contacts SET last_name = :rec.last_name, email = :rec.email, credit = :rec.credit WHERE id = :id;
    END IF
NEXT
IF (SELECT last_name FROM contacts WHERE id = 1) <> "JONES" THEN ERROR 1, "hash field GET with @!"
IF (SELECT email FROM contacts WHERE id = 1) <> "a@x.com" THEN ERROR 1, "untouched hash field"
IF (SELECT credit FROM contacts WHERE id = 1) <> 250 THEN ERROR 1, "numeric hash field with VALID"

DIM a(3)
a(1) = "one"
h.ship.city = "Boston"
@ 9, 1 SAY "a(1): " GET a(1)
@ 10, 1 SAY "city: " GET h.ship.city
@ 11, 1 SAY "zip:  " GET h.zip$
REM Keys: Ctrl-Y "uno" Tab Ctrl-Y "Austin" Tab "02116" Enter
READ
IF a(1) <> "uno" THEN ERROR 1, "array element GET: " & a(1)
IF h.ship.city <> "Austin" THEN ERROR 1, "nested hash field GET: " & h.ship.city
IF h.zip$ <> "02116" THEN ERROR 1, "new hash key GET: " & h.zip$

REM Esc puts every field back, including hash fields
@ 10, 1 SAY "city: " GET h.ship.city
@ 9, 1 SAY "a(1): " GET a(1)
REM Keys: Ctrl-Y "zzz" Tab Ctrl-Y "yyy" Esc
READ
IF h.ship.city <> "Austin" OR a(1) <> "uno" THEN ERROR 1, "Esc should restore hash fields and elements"

ON ERROR GOTO whole
@ 12, 1 GET h
ERROR 1, "GET of a whole hash should fail"
whole:
IF INSTR(ERRMSG$, "GET one of its fields") = 0 THEN ERROR 1, "whole-hash message: " & ERRMSG$
RESUME done
done:
ON ERROR GOTO 0
COLOR 7, 0
CLS
PRINT "get_targets: all checks passed"
REM EXPECT: get_targets: all checks passed
