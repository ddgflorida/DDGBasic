REM --- Setup and get table list (same as before) ---
DATABASE OPEN "sample_app.db"

REM Use CREATE TABLE IF NOT EXISTS so this setup is safe to run multiple times.
CREATE TABLE IF NOT EXISTS employees (
    employee_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    hire_date TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT,
    price REAL,
    stock_quantity INTEGER
);

REM Only insert data if the employees table is empty.
LET cnt = (SELECT COUNT(*) FROM employees)
IF cnt = 0 THEN
    INSERT INTO employees VALUES (1, 'Nancy', 'Davolio', '2023-05-01');
    INSERT INTO employees VALUES (2, 'Andrew', 'Fuller', '2023-08-14');
END IF
LET cnt = (SELECT COUNT(*) FROM products)
IF cnt = 0 THEN
    INSERT INTO products VALUES (1, 'BBQ Sauce', 20.33, 99);
    INSERT INTO products VALUES (2, 'Ketchup', 3.44, 876);
END IF
DIM table_list AS ARRAY
DIM temp_hash AS HASH
FOR temp_hash IN (SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name)
    PUSH table_list, temp_hash.NAME
NEXT

REM --- Define the form using the new, cleaner syntax ---
FORM table_chooser
    HEADING "Select Table to Edit"
    
    FIELD selected_table TYPE CHOICE SOURCE table_list LABEL "Please choose a table"

    BUTTON "Edit Table" ACTION "SUBMIT"
    BUTTON "Cancel"     ACTION "CANCEL"
ENDFORM

REM --- Run the form and process the selection ---
OPENFORM table_chooser

IF FORM_RESULT$ = "SUBMIT" THEN
    REM The selected value is now directly in the FORM_DATA hash
    table_to_edit$ = FORM_DATA.SELECTED_TABLE
    
    PRINT
    PRINT "Loading editor for table: '" + table_to_edit$ + "'..."
    GRIDEDIT table_to_edit$
ELSE
    PRINT "Operation cancelled."
END IF

END