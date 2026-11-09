REM MAKE FORM on SQLite and DuckDB: the program it writes is checked, then run with keys
REM from the test runner: add a row (refused by a CHECK, then fixed), edit it, delete another.
prog$ = "_make_form_prog.bas"
DATABASE ENGINE SQLITE
db$ = "_make_form.db"
GOSUB setup
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email VARCHAR(40), state TEXT REFERENCES states(code),
                        joined DATE, credit DECIMAL(10, 2) CHECK (credit >= 0), active BOOLEAN, visits INTEGER);
INSERT INTO customers (name, email, state, joined, credit, active, visits) VALUES ('Ann Lee', 'ann@example.com', 'FL', '2024-01-15', 1500.5, 1, 3);
GOSUB make_and_run
REM EXPECT: a program for customers with 7 fields
REM EXPECT: CHECK constraint failed
DATABASE ENGINE DUCKDB
db$ = "_make_form.duckdb"
GOSUB setup
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email VARCHAR(40), state TEXT REFERENCES states(code),
                        joined DATE, credit DECIMAL(10, 2) CHECK (credit >= 0), active BOOLEAN, visits INTEGER);
INSERT INTO customers VALUES (1, 'Ann Lee', 'ann@example.com', 'FL', '2024-01-15', 1500.5, true, 3);
GOSUB make_and_run
REM EXPECT: a program for customers with 8 fields
COLOR 7, 0
CLS
PRINT "make_form: all checks passed"
REM EXPECT: make_form: all checks passed
END

setup:
    IF FILE_EXISTS(db$) THEN KILL db$
    IF FILE_EXISTS(prog$) THEN KILL prog$
    DATABASE OPEN db$
    CREATE TABLE states (code TEXT PRIMARY KEY, name TEXT);
    INSERT INTO states VALUES ('CA', 'California'), ('FL', 'Florida'), ('NY', 'New York');
    RETURN

make_and_run:
    MAKE FORM "customers" TO prog$ TITLE "Customers"
    READ FILE prog$ INTO src$
    IF INSTR(src$, "LIST (SELECT code FROM states ORDER BY 1)") = 0 THEN ERROR 1, "a foreign key should be a LIST"
    IF INSTR(src$, "GET r.joined PICTURE " + CHR$(34) + "@D") = 0 THEN ERROR 1, "a DATE should be @D"
    IF INSTR(src$, "GET r.active CHECKBOX") = 0 THEN ERROR 1, "a BOOLEAN should be a CHECKBOX"
    IF INSTR(src$, "GET r.credit PICTURE " + CHR$(34) + "99,999,999.99") = 0 THEN ERROR 1, "DECIMAL(10, 2) mask"
    IF INSTR(src$, "GET r.name PICTURE " + CHR$(34) + "@S") = 0 OR INSTR(src$, "REQUIRED MESSAGE") = 0 THEN ERROR 1, "NOT NULL should be REQUIRED"
    REM Keys: see run_tests.py. Add Bob with credit -5 (refused), fix it, save;
    REM edit Bob's visits to 9; delete Ann; quit
    RUN prog$
    DATABASE OPEN db$
    IF (SELECT COUNT(*) FROM customers) <> 1 THEN ERROR 1, "Ann should be deleted"
    IF (SELECT COUNT(*) FROM customers WHERE name = 'Bob' AND email = 'bob@example.com' AND state = 'NY'
        AND CAST(joined AS VARCHAR) = '2025-01-01' AND credit = 5 AND visits = 9) <> 1 THEN ERROR 1, "Bob's row"
    IF (SELECT COUNT(*) FROM customers WHERE active) <> 1 THEN ERROR 1, "Bob should be active"
    DATABASE CLOSE
    KILL db$
    KILL prog$
    RETURN
