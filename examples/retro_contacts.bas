REM ===================================================================
REM Contacts: a 1990s-style data entry screen.
REM Blue screen, a light-bar main menu, @ SAY/GET entry with picture
REM masks and VALID checks, and BROWSE to pick a record.
REM Keys: arrows/Tab move, Enter accepts, Esc cancels, Ctrl-Y clears a field.
REM ===================================================================
DATABASE OPEN ":memory:"
CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, state TEXT, credit REAL);
INSERT INTO contacts (name, phone, state, credit) VALUES
    ('ACME CORP', '(555) 123-4567', 'FL', 1000),
    ('GLOBEX', '(555) 999-0000', 'NY', 250.5),
    ('INITECH', '(555) 444-1212', 'TX', 0);

main:
    GOSUB draw_frame
    @ 4, 30 SAY "Main Menu"
    item = MENU(6, 28, "Browse contacts", "Add a contact", "Edit a contact", "Delete a contact", "Quit")
    IF item = 1 THEN GOSUB browse_contacts
    IF item = 2 THEN GOSUB add_contact
    IF item = 3 THEN GOSUB edit_contact
    IF item = 4 THEN GOSUB delete_contact
    IF item = 0 OR item = 5 THEN GOTO done
    GOTO main

done:
    COLOR 7, 0
    CLS
    PRINT "Goodbye."; (SELECT COUNT(*) FROM contacts); " contacts on file."
    END

draw_frame:
    COLOR 15, 1, 0, 3
    CLS
    BOX 1, 1, 20, 78, "CONTACTS  " & DATE$ DOUBLE
    @ 19, 3 SAY "Arrows/Tab move   Enter accepts   Esc cancels   Ctrl-Y clears a field"
    RETURN

browse_contacts:
    REM An editable grid: arrows move between cells, Enter or typing edits a cell, Esc ends
    BROWSE (SELECT id, name, phone, state, credit FROM contacts ORDER BY name) EDIT KEY "id" AT 3, 4, 17, 75 TITLE "Contacts (Enter edits a cell)"
    RETURN

add_contact:
    name$ = "" : phone$ = "" : state$ = "" : credit = 0
    GOSUB entry_screen
    IF LASTKEY$ = CHR$(27) THEN RETURN
    INSERT INTO contacts (name, phone, state, credit) VALUES (:name$, :phone$, :state$, :credit);
    GOSUB saved_message
    RETURN

edit_contact:
    BROWSE (SELECT id, name, phone, state, credit FROM contacts ORDER BY name) AT 3, 4, 17, 75 TITLE "Pick a contact to edit" INTO picked
    IF LASTKEY$ = CHR$(27) THEN RETURN
    id = picked.id : name$ = picked.name : phone$ = picked.phone : state$ = picked.state : credit = picked.credit
    GOSUB draw_frame
    GOSUB entry_screen
    IF LASTKEY$ = CHR$(27) THEN RETURN
    UPDATE contacts SET name = :name$, phone = :phone$, state = :state$, credit = :credit WHERE id = :id;
    GOSUB saved_message
    RETURN

delete_contact:
    BROWSE (SELECT id, name, phone FROM contacts ORDER BY name) AT 3, 4, 17, 75 TITLE "Pick a contact to delete" INTO picked
    IF LASTKEY$ = CHR$(27) THEN RETURN
    id = picked.id
    @ 18, 4 SAY "Delete " & picked.name & "?"
    answer = MENU(12, 30, "No", "Yes")
    IF answer = 2 THEN
        DELETE FROM contacts WHERE id = :id;
    END IF
    RETURN

entry_screen:
    BOX 5, 10, 13, 68, "Contact"
    @ 7, 13 SAY "Name   : " GET name$ PICTURE "@!S30" VALID LEN(TRIM$(name$)) > 0
    @ 8, 13 SAY "Phone  : " GET phone$ PICTURE "(999) 999-9999"
    @ 9, 13 SAY "State  : " GET state$ PICTURE "!!"
    @ 10, 13 SAY "Credit : " GET credit PICTURE "999999.99" VALID credit >= 0 AND credit <= 100000
    READ
    RETURN

saved_message:
    @ 15, 13 SAY "Saved: " & name$
    k$ = INKEY$(1.5)
    RETURN
