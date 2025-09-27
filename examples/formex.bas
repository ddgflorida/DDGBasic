REM ===================================================================
REM DbBasic Form Example: A simple contact manager
REM This script demonstrates creating a database, defining forms,
REM and interacting with the data in a loop.
REM ===================================================================

REM ---
REM Part 1: Database Setup
REM Create a SQLite database and populate it with sample contacts.
REM ---
PRINT "Setting up the database..."
DATABASE OPEN "contacts.db"

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT
);
LET cnt = (SELECT COUNT(*) FROM contacts)
IF cnt = 0 THEN
INSERT INTO contacts (first_name, last_name, email) VALUES
('John', 'Smith', 'john.smith@example.com'),
('Jane', 'Doe', 'jane.doe@example.com'),
('Peter', 'Jones', 'peter.jones@example.com');
END IF

PRINT "Database 'contacts.db' created and populated."

REM ---
REM Part 2: Form Definitions
REM We define two forms: one to show the list and one for data entry.
REM ---

REM This form displays a list (grid) of all contacts.
FORM contacts_list
    SOURCE (SELECT id, last_name, first_name, email FROM contacts ORDER BY last_name)
    DISPLAY 10                 REM Display up to 10 rows, which triggers the grid view.
    HEADING "Contact List"

    REM Define the fields to show in the grid. The names must match the SOURCE query.
    FIELD last_name  TYPE TEXT LABEL "Last Name"
    FIELD first_name TYPE TEXT LABEL "First Name"
    FIELD email      TYPE TEXT LABEL "Email Address"

    REM Define buttons for the user to interact with the list.
    BUTTON "View Edit" ACTION "EDIT"   REM A custom action to signal we want to edit.
    BUTTON "Close"     ACTION "CLOSE"  REM An action to exit the application.
ENDFORM

REM This form displays a single record for editing.
FORM contacts_entry
    SOURCE (SELECT id, first_name, last_name, email FROM contacts)
    DISPLAY 1                  REM Displaying 1 row triggers the single-record entry view.
    HEADING "Contact Details"

    FIELD first_name TYPE TEXT LABEL "First Name"
    FIELD last_name  TYPE TEXT LABEL "Last Name"
    FIELD email      TYPE TEXT LABEL "Email Address"

    BUTTON "Update" ACTION "UPDATE"
    BUTTON "Cancel" ACTION "CANCEL"
ENDFORM

REM ---
REM Part 3: Main Application Loop
REM This loop shows the contact list and waits for user action.
REM ---
DO
    PRINT "Loading contact list..."
    OPENFORM contacts_list

    REM The FORM_RESULT$ variable is automatically set when a form closes.
    IF FORM_RESULT$ = "CLOSE" OR FORM_RESULT$ = "" THEN
        EXIT DO  REM Exit the main loop if the user clicks "Close".

    ELSEIF FORM_RESULT$ = "EDIT" THEN
        REM The user clicked "View/Edit". The ID of the selected row is now in FORM_SELECTED_ID.
        PRINT "Editing record ID: " + STR$(FORM_SELECTED_ID)
        
        REM Now, open the entry form, telling it WHICH record to load using the USING clause.
        OPENFORM contacts_entry USING FORM_SELECTED_ID
        
        REM After the entry form closes, check its result.
        IF FORM_RESULT$ = "UPDATE" THEN
            PRINT "Updating record in the database..."
            
            REM Unpack the values from the FORM_DATA hash into top-level variables
            REM so the SQL statement can find them.
            FIRST_NAME = FORM_DATA.FIRST_NAME
            LAST_NAME = FORM_DATA.LAST_NAME
            EMAIL = FORM_DATA.EMAIL
            ID = FORM_SELECTED_ID    REM Use the ID from the form result
            
            UPDATE contacts
               SET first_name = :FIRST_NAME,
                   last_name = :LAST_NAME,
                   email = :EMAIL
             WHERE id = :ID;
             
            PRINT "Record PK(" + STR$(FORM_SELECTED_ID) + ") updated."
        END IF
    END IF
LOOP

PRINT
PRINT "Application finished."
