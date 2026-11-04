REM Test script for Fixed-Width file loading and querying
REM Creates a sample fixed-width file, loads it into SQLite, and runs queries

PRINT "Fixed-Width Load Test Script"
PRINT "==========================="
PRINT

REM Create a sample fixed-width file with employee data
REM Format: Name (20 chars), Department (10 chars), Salary (8 chars)
PRINT "Creating sample fixed-width file..."
OPEN "employees.txt" FOR OUTPUT AS #1

REM Write sample employee records (fixed positions)
REM                 1         2         3
REM        123456789012345678901234567890123456789
PRINT #1, "John Smith          Engineering75000   "
PRINT #1, "Jane Doe            Marketing  65000   "
PRINT #1, "Bob Johnson         Engineering80000   "
PRINT #1, "Alice Brown         Sales      55000   "
PRINT #1, "Mike Wilson         Engineering72000   "
PRINT #1, "Sarah Davis         Marketing  60000   "
PRINT #1, "Tom Anderson        Sales      58000   "

CLOSE #1
PRINT "Created employees.txt with 7 employee records"
PRINT "Format: Name(1-20), Department(21-31), Salary(32-39)"
PRINT
SHELL "type employees.txt"

REM Load the fixed-width file into a SQLite table
PRINT "Loading fixed-width file into SQLite table..."
LOAD FIXED "employees.txt" CREATE TABLE employees OPTIONS "fields=name:1-20,department:21-31,salary:32-39"

IF ERR = 0 THEN
    PRINT "Fixed-width file loaded successfully into 'employees' table"
ELSE
    PRINT "Error loading file: "; ERRMSG$
    END
END IF

PRINT

REM Run some SELECT queries to verify the data
PRINT "Running SELECT queries..."
PRINT
PRINT "1. All employees:"
PRINT "=================="
SELECT * FROM employees ORDER BY name;

PRINT
PRINT "2. Engineering department only:"
PRINT "==============================="
SELECT name, salary FROM employees WHERE department = 'Engineering' ORDER BY salary DESC;

PRINT
PRINT "3. Average salary by department:"
PRINT "================================"
SELECT department, AVG(CAST(salary AS INTEGER)) as avg_salary FROM employees GROUP BY department ORDER BY avg_salary DESC;

PRINT
PRINT "4. High earners (salary > 70000):"
PRINT "=================================="
SELECT name, department, salary FROM employees WHERE CAST(salary AS INTEGER) > 70000 ORDER BY CAST(salary AS INTEGER) DESC;

PRINT
PRINT "5. Employee count by department:"
PRINT "================================"
SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department ORDER BY employee_count DESC;

PRINT
PRINT "Test completed successfully!"

REM Clean up - remove the test file
KILL "employees.txt"
PRINT "Cleaned up test file"

END