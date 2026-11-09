REM Contact screen: a simple entry form saved with one INSERT. The record is a hash (c.name,
REM c.phone, ...), so its fields bind straight into the SQL as :c.name and so on.
REM Keys: Tab or Enter = next field, Space or F2 = open the State list or tick Active,
REM Esc = cancel. The mouse works too.
REM Change ":memory:" to a file name, such as "contacts.db", to keep the contacts.
DATABASE OPEN ":memory:"
CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, state TEXT, active TEXT);

c.name = "" : c.phone = "" : c.email = "" : c.state = "FL" : c.active = "Y"

COLOR 15, 1, 0, 3
CLS
BOX 3, 10, 14, 70, "Contact" DOUBLE SHADOW
@ 5, 13 SAY "Name   : " GET c.name PICTURE "@S30" REQUIRED MESSAGE "A name is required"
@ 6, 13 SAY "Phone  : " GET c.phone PICTURE "@R (999) 999-9999"
@ 7, 13 SAY "Email  : " GET c.email PICTURE "@S35"
@ 8, 13 SAY "State  : " GET c.state LIST "CA,FL,NY,TX,WA"
@ 9, 13 SAY "Active : " GET c.active CHECKBOX
@ 12, 25 BUTTON "Save"
@ 12, 35 BUTTON "Cancel" CANCEL
READ

COLOR 7, 0
CLS
IF BUTTON$ = "Save" THEN
    INSERT INTO contacts (name, phone, email, state, active) VALUES (:c.name, :c.phone, :c.email, :c.state, :c.active);
    PRINT "Saved "; c.name
    SELECT name, phone, email, state, active FROM contacts;
ELSE
    PRINT "Cancelled."
END IF
REM EXPECT: Saved Ann Lee
REM EXPECT: | Ann Lee | 5551234567 | ann@example.com | NY    | N      |
