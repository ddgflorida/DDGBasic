REM MAKE FORM demo: makes a small shop database, then writes a complete data-entry program
REM for its customers table: a menu bar, an editable grid, an entry form whose fields come
REM from the column types (a drop-down for the state, which references the states table,
REM a date, a money mask, a check box), hints, and F1 help.
REM Run this, then run the program it writes:  ddgbasic customers_form.bas
IF FILE_EXISTS("shop.db") THEN KILL "shop.db"
IF FILE_EXISTS("customers_form.bas") THEN KILL "customers_form.bas"
DATABASE OPEN "shop.db"
CREATE TABLE states (code TEXT PRIMARY KEY, name TEXT);
INSERT INTO states VALUES ('CA', 'California'), ('FL', 'Florida'), ('NY', 'New York'), ('TX', 'Texas');
CREATE TABLE customers (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    email   VARCHAR(40),
    state   TEXT REFERENCES states(code),
    joined  DATE,
    credit  DECIMAL(10, 2) CHECK (credit >= 0),
    active  BOOLEAN,
    notes   TEXT);
INSERT INTO customers (name, email, state, joined, credit, active) VALUES
    ('Acme Corp', 'orders@acme.example', 'FL', '2019-03-01', 1000, 1),
    ('Globex', 'info@globex.example', 'NY', '2021-07-15', 250.5, 1);

MAKE FORM "customers" TO "customers_form.bas"
REM EXPECT: Wrote customers_form.bas: a program for customers with 7 fields.
