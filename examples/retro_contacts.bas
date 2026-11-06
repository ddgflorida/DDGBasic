REM ===================================================================
REM Contacts: a 1990s-style DbBasic application.
REM A menu bar, an editable grid that sorts and colours its rows, entry
REM forms with drop-down lists, check boxes, dates and field hints, F1
REM help from anywhere, a memo editor, a report and message boxes, in
REM about a hundred and fifty lines. Chapter 7 of the manual walks through it.
REM ===================================================================
DATABASE OPEN ":memory:"
CREATE TABLE states (code TEXT PRIMARY KEY, name TEXT);
INSERT INTO states VALUES ('CA', 'California'), ('FL', 'Florida'), ('NY', 'New York'), ('TX', 'Texas');
CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, email TEXT, state TEXT,
                       active TEXT DEFAULT 'Y', since TEXT, credit REAL CHECK (credit >= 0), notes TEXT);
INSERT INTO contacts (name, phone, email, state, active, since, credit) VALUES
    ('ACME CORP', '(555) 123-4567', 'orders@acme.example', 'FL', 'Y', '2019-03-01', 1000),
    ('GLOBEX', '(555) 999-0000', 'info@globex.example', 'NY', 'Y', '2021-07-15', 250.5),
    ('INITECH', '(555) 444-1212', 'tps@initech.example', 'TX', 'N', '2018-11-30', 0);

REM F1 shows the keys from anywhere: the menu bar, a form, the grid, the editor
keys$ = "F1           This help, from anywhere" + CHR$(10)
keys$ = keys$ + "Menu bar     Left/Right move, Enter or a letter opens a menu" + CHR$(10)
keys$ = keys$ + "Forms        Tab/Enter next field, Space or F2 opens a list" + CHR$(10)
keys$ = keys$ + "             or ticks a box, Esc cancels" + CHR$(10)
keys$ = keys$ + "Grid         Enter edits a cell, Ins adds a row, Del deletes," + CHR$(10)
keys$ = keys$ + "             click a heading or press F3 to sort" + CHR$(10)
keys$ = keys$ + "Pick lists   Type a name to jump to it" + CHR$(10)
keys$ = keys$ + "Notes        Ctrl-W saves, Esc cancels" + CHR$(10)
keys$ = keys$ + "Viewer       / finds, n finds the next, q closes"
FUNCTION show_help()
    VIEW keys$ AT 5, 8, 17, 74 TITLE "Keys (Esc closes)"
END FUNCTION
ON KEY "F1" CALL show_help

GOSUB desktop
DO
    GOSUB summary
    choice$ = MENUBAR$("File:Report|-|Quit", "Contacts:Browse|Add|Edit|Notes|Delete", "Help:Keys|About")
    IF choice$ = "File.Report" THEN GOSUB report
    IF choice$ = "Contacts.Browse" THEN GOSUB browse_contacts
    IF choice$ = "Contacts.Add" THEN GOSUB add_contact
    IF choice$ = "Contacts.Edit" THEN GOSUB edit_contact
    IF choice$ = "Contacts.Notes" THEN GOSUB edit_notes
    IF choice$ = "Contacts.Delete" THEN GOSUB delete_contact
    IF choice$ = "Help.Keys" THEN x = show_help()
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
    @ 24, 2 SAY "F1 help  Arrows move  Enter chooses  Esc goes back  Letters are hot keys"
    RETURN

summary:
    REM The opening screen: the contacts on file, redrawn after every command.
    REM Inactive contacts are shown in grey.
    BOX 3, 3, 21, 78, "Contacts on file"
    @ 5, 6 SAY PADRIGHT$("Name", 20, " ") & " " & PADRIGHT$("Phone", 16, " ") & " " & PADRIGHT$("State", 5, " ") & "    Credit"
    @ 6, 6 SAY REPEAT$("-", 53)
    row = 7
    FOR s IN (SELECT name, phone, state, credit, active FROM contacts ORDER BY name LIMIT 12)
        IF s.active = "N" THEN COLOR 7
        @ row, 6 SAY PADRIGHT$(s.name, 20, " ") & " " & PADRIGHT$(s.phone, 16, " ") & " " & PADRIGHT$(s.state, 5, " ") & FORMAT$(s.credit, "###,##0.00")
        COLOR 15
        row = row + 1
    NEXT
    @ 20, 6 SAY LTRIM$(STR$((SELECT COUNT(*) FROM contacts))) & " contacts.  Press C for Contacts, F for File, H for Help."
    RETURN

browse_contacts:
    REM The whole list, editable: Enter or typing edits a cell, Ins adds, Del deletes.
    REM Id and name stay in view while the other columns scroll, credit is shown with
    REM commas, and the query gives inactive contacts grey rows.
    BROWSE (SELECT id, name, phone, email, state, active, since, credit,
                   CASE WHEN active = 'N' THEN 7 END AS shade
              FROM contacts ORDER BY name) EDIT KEY "id" _
        AT 3, 3, 21, 78 TITLE "Contacts (Enter edits, Ins adds, Del deletes, F3 sorts)" _
        FREEZE 2 FORMAT credit "###,##0.00" COLOR "shade"
    RETURN

pick_contact:
    REM Choose one contact; c gets the row, or an empty hash after Esc. Typing a name jumps to it.
    BROWSE (SELECT name, phone, state, id FROM contacts ORDER BY name) AT 3, 3, 21, 78 TITLE "Pick a contact (type a name)" INTO c
    RETURN

add_contact:
    c.name = "" : c.phone = "" : c.email = "" : c.state = "FL" : c.active = "Y" : c.since = DATE$ : c.credit = 0
    saved$ = SAVESCREEN()
    BOX 5, 12, 18, 68, "New contact" SHADOW
    @ 7, 15 SAY "Name   : " GET c.name PICTURE "@!S30" VALID LEN(TRIM$(c.name)) > 0 MESSAGE "A name is required" _
        HINT "The company or person's name (required)"
    @ 8, 15 SAY "Phone  : " GET c.phone PICTURE "(999) 999-9999" HINT "Ten digits: the brackets and dash are filled in"
    @ 9, 15 SAY "Email  : " GET c.email PICTURE "@S30" HINT "Optional"
    @ 10, 15 SAY "State  : " GET c.state LIST (SELECT code FROM states ORDER BY code) _
        HINT "Space or F2 opens the list; a letter jumps to a state"
    @ 11, 15 SAY "Active : " GET c.active CHECKBOX HINT "Space ticks or clears the box"
    @ 12, 15 SAY "Since  : " GET c.since PICTURE "@D" HINT "When they became a customer: YYYY-MM-DD"
    @ 13, 15 SAY "Credit : " GET c.credit PICTURE "999,999.99" VALID c.credit >= 0 AND c.credit <= 100000 _
        MESSAGE "Credit must be 0 to 100,000" HINT "Credit limit in dollars, 0 to 100,000"
    @ 16, 15 BUTTON "Save"
    @ 16, 25 BUTTON "Cancel" CANCEL
    READ
    RESTSCREEN saved$
    IF BUTTON$ <> "Save" THEN RETURN
    INSERT INTO contacts (name, phone, email, state, active, since, credit)
        VALUES (:c.name, :c.phone, :c.email, :c.state, :c.active, :c.since, :c.credit);
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
    REPORT (SELECT state, name, active, credit FROM contacts ORDER BY state, name) _
        TITLE "Contacts by state" GROUP BY state TOTAL credit FORMAT credit "###,##0.00" TO VIEW
    RETURN
