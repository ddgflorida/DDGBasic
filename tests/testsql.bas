REM --- Comprehensive Procedural SQL Test Suite ---

PRINT "--- Initializing Database ---"
DATABASE OPEN "test_suite.db"

REM Drop the table if it exists from a previous failed run
DROP TABLE IF EXISTS employees;

CREATE TABLE employees (
  id INTEGER PRIMARY KEY,
  name TEXT,
  department TEXT,
  salary INTEGER
);

REM --- Test Case 1: Transaction Rollback ---
PRINT
PRINT "--- Testing Transaction Rollback ---"

BEGIN TRANSACTION;
  INSERT INTO employees VALUES (101, 'Alice', 'Engineering "Smarties"', 80000);
  INSERT INTO employees VALUES (102, 'Bob', 'Marketing', 65000);
COMMIT;

BEGIN TRANSACTION;
  INSERT INTO employees VALUES (103, 'Charlie', 'Engineering', 95000);
  UPDATE employees SET salary = 70000 WHERE name = 'Bob';
ROLLBACK;

LET total_employees = (SELECT COUNT(*) FROM employees)
PRINT "Employee count after rollback:", total_employees ' Should be 2

IF total_employees = 2 THEN
    PRINT "OK: Rollback successful."
ELSE
    PRINT "FAIL: Rollback did not work."
END IF

LET bobs_salary = (SELECT salary FROM employees WHERE name = 'Bob')
IF bobs_salary = 65000 THEN
    PRINT "OK: Bob''s salary was not updated."
ELSE
    PRINT "FAIL: Bob''s salary was updated despite rollback."
END IF

REM --- Test Case 2: IF EXISTS and NOT EXISTS ---
PRINT
PRINT "--- Testing IF EXISTS / NOT EXISTS ---"

IF EXISTS (SELECT * FROM employees WHERE name = 'Alice') THEN
  PRINT "OK: Found Alice (who should exist)."
ELSE
  PRINT "FAIL: Did not find Alice."
END IF

IF NOT EXISTS (SELECT * FROM employees WHERE name = 'Charlie') THEN
  PRINT "OK: Did not find Charlie (who was rolled back)."
ELSE
  PRINT "FAIL: Found Charlie, who should not exist."
END IF

REM --- Test Case 3: Complex SQL String Parsing ---
INSERT INTO employees VALUES (104, 'O''Malley (HR)', 'Human Resources', 55000);

IF EXISTS (SELECT * FROM employees WHERE name = 'O''Malley (HR)') THEN
    PRINT "OK: Correctly parsed complex SQL string with quotes and parens."
ELSE
    PRINT "FAIL: Did not parse complex SQL string correctly."
END IF


REM --- Test Case 4: FOR...IN loop ---
PRINT
PRINT "--- Testing FOR...IN Loop ---"
PRINT "Current Employees:"
FOR rec IN (SELECT id, name, department FROM employees ORDER BY id) 
  PRINT "  ID:"; rec.id, "Name:", rec.name$, "Dept:", rec.department$
NEXT

REM -- Test Case 5: SELECT with SET OUTPUT CONSOLE
PRINT
PRINT "--- Testing SET OUTPUT... with SELECT ---"
SET OUTPUT CONSOLE
select id,name,department FROM employees ORDER BY id;

PRINT
PRINT "--- Testing SET OUTPUT CONSOLE FORMAT JSON ... with SELECT ---"
SET OUTPUT CONSOLE FORMAT JSON
select id,name,department FROM employees ORDER BY id;

PRINT
PRINT "--- Testing SET OUTPUT CONSOLE FORMAT JSONL ... with SELECT ---"
SET OUTPUT CONSOLE FORMAT JSONL
select id,name,department FROM employees ORDER BY id;

PRINT
PRINT "--- Testing SET OUTPUT CONSOLE FORMAT CSV ... with SELECT ---"
SET OUTPUT CONSOLE FORMAT CSV
select id,name,department FROM employees ORDER BY id;


REM --- Final Cleanup ---
DROP TABLE employees;
DATABASE CLOSE
PRINT
PRINT "--- Test Suite Complete ---"

END