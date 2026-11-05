REM ===================================================================
REM Contacts: a 1990s-style DbBasic application.
REM A menu bar, an editable grid, entry forms with a lookup list and
REM checks, a memo editor, a report viewer and message boxes, in about
REM a hundred lines. Chapter 7 of the manual walks through it.
REM ===================================================================
DATABASE OPEN ":memory:"
CREATE TABLE states (code TEXT PRIMARY KEY, name TEXT);
INSERT INTO states VALUES ('CA', 'California'), ('FL', 'Florida'), ('NY', 'New York'), ('TX', 'Texas');
CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, state TEXT,
                       credit REAL CHECK (credit >= 0), notes TEXT);
INSERT INTO contacts (name, phone, state, credit) VALUES
    ('ACME CORP', '(555) 123-4567', 'FL', 1000),
    ('GLOBEX', '(555) 999-0000', 'NY', 250.5),
    ('INITECH', '(555) 444-1212', 'TX', 0);

GOSUB desktop
DO
    choice$ = MENUBAR$("File:Report|-|Quit", "Contacts:Browse|Add|Edit|Notes|Delete", "Help:Keys|About")
    IF choice$ = "File.Report" THEN GOSUB report
    IF choice$ = "Contacts.Browse" THEN GOSUB browse_contacts
    IF choice$ = "Contacts.Add" THEN GOSUB add_contact
    IF choice$ = "Contacts.Edit" THEN GOSUB edit_contact
    IF choice$ = "Contacts.Notes" THEN GOSUB edit_notes
    IF choice$ = "Contacts.Delete" THEN GOSUB delete_contact
    IF choice$ = "Help.Keys" THEN GOSUB show_keys
    IF choice$ = "Help.About" THEN x = ALERT("Contacts;A DbBasic text-mode application")
LOOP UNTIL choice$ = "File.Quit" OR choice$ = ""
COLOR 7, 0
CLS
PRINT "Goodbye."; (SELECT COUNT(*) FROM contacts); " contacts on file."
END
REM The test runner plays a scripted session (add one contact, delete one) and checks for:
REM EXPECT: Goodbye. 3 contacts on file.

desktop:
    COLOR 15, 1, 0, 3
    CLS
    BOX 2, 1, 23, 80, "CONTACTS  " & DATE$ DOUBLE
    @ 24, 2 SAY "Arrows move  Enter chooses  Esc goes back  Letters are hot keys"
    RETURN

browse_contacts:
    REM The whole list, editable: Enter or typing edits a cell, Ins adds, Del deletes
    BROWSE (SELECT id, name, phone, state, credit FROM contacts ORDER BY name) EDIT KEY "id" _
        AT 3, 3, 21, 78 TITLE "Contacts (Enter edits, Ins adds, Del deletes)"
    RETURN

pick_contact:
    REM Choose one contact; c gets the row, or an empty hash after Esc
    BROWSE (SELECT id, name, phone FROM contacts ORDER BY name) AT 3, 3, 21, 78 TITLE "Pick a contact" INTO c
    RETURN

add_contact:
    c.name = "" : c.phone = "" : c.state = "" : c.credit = 0
    saved$ = SAVESCREEN()
    BOX 6, 12, 15, 68, "New contact"
    @ 8, 15 SAY "Name   : " GET c.name PICTURE "@!S30" VALID LEN(TRIM$(c.name)) > 0 MESSAGE "A name is required"
    @ 9, 15 SAY "Phone  : " GET c.phone PICTURE "(999) 999-9999"
    @ 10, 15 SAY "State  : " GET c.state PICTURE "!!" LOOKUP (SELECT code, name FROM states ORDER BY code)
    @ 11, 15 SAY "Credit : " GET c.credit VALID c.credit >= 0 AND c.credit <= 100000 MESSAGE "Credit must be 0 to 100,000"
    @ 13, 15 SAY "Tab: next field   F2: list of states   Esc: cancel"
    READ
    RESTSCREEN saved$
    IF LASTKEY$ = CHR$(27) THEN RETURN
    INSERT INTO contacts (name, phone, state, credit) VALUES (:c.name, :c.phone, :c.state, :c.credit);
    x = ALERT("Saved " & c.name)
    RETURN

edit_contact:
    GOSUB pick_contact
    IF LASTKEY$ = CHR$(27) THEN RETURN
    EDIT RECORD (SELECT id, name, phone, state, credit FROM contacts WHERE id = :c.id) TITLE "Edit contact"
    RETURN

edit_notes:
    GOSUB pick_contact
    IF LASTKEY$ = CHR$(27) THEN RETURN
    FOR rec IN (SELECT id, name, notes FROM contacts WHERE id = :c.id)
        EDIT TEXT rec.notes AT 5, 10, 18, 70 TITLE "Notes: " & rec.name
        IF LASTKEY$ <> CHR$(27) THEN UPDATE contacts SET notes = :rec.notes WHERE id = :rec.id;
    NEXT
    RETURN

delete_contact:
    GOSUB pick_contact
    IF LASTKEY$ = CHR$(27) THEN RETURN
    IF ALERT("Delete " & c.name & "?", "No", "Yes") = 2 THEN DELETE FROM contacts WHERE id = :c.id;
    RETURN

report:
    VIEW (SELECT state, COUNT(*) AS contacts, SUM(credit) AS credit FROM contacts GROUP BY state ORDER BY state) _
        AT 3, 3, 21, 78 TITLE "Contacts by state (q closes)"
    RETURN

show_keys:
    keys$ = "Menu bar     Left/Right move, Enter or a letter opens a menu" + CHR$(10)
    keys$ = keys$ + "Forms        Tab/Enter next field, F2 list, Esc cancel" + CHR$(10)
    keys$ = keys$ + "Grid         Enter edits a cell, Ins adds a row, Del deletes" + CHR$(10)
    keys$ = keys$ + "Notes        Ctrl-W saves, Esc cancels" + CHR$(10)
    keys$ = keys$ + "Viewer       / finds, n finds the next, q closes"
    VIEW keys$ AT 6, 8, 14, 74 TITLE "Keys"
    RETURN
