REM Test script for CSV loading and querying
REM Creates a sample CSV file, loads it into SQLite, and runs queries

PRINT "CSV Load Test Script"
PRINT "==================="
PRINT

REM Create a sample CSV file with employee data
PRINT "Creating sample CSV file..."
OPEN "employees.csv" FOR OUTPUT AS #1

REM Write header row
PRINT #1, "name,department,salary"

REM Write sample employee records
PRINT #1, "John Smith,Engineering,75000"
PRINT #1, "Jane Doe,Marketing,65000"
PRINT #1, "Bob Johnson,Engineering,80000"
PRINT #1, "Alice Brown,Sales,55000"
PRINT #1, "Mike Wilson,Engineering,72000"
PRINT #1, "Sarah Davis,Marketing,60000"
PRINT #1, "Tom Anderson,Sales,58000"

CLOSE #1
PRINT "Created employees.csv with 7 employee records"
PRINT

REM Load the CSV into a SQLite table
PRINT "Loading CSV into SQLite table..."
LOAD CSV "employees.csv" CREATE "employees" OPTIONS "header=true"
REM LOAD CSV "employees.csv" CREATE "employees" OPTIONS "header=true,linenum=1"

IF ERR = 0 THEN
    PRINT "CSV loaded successfully into 'employees' table"
ELSE
    PRINT "Error loading CSV: "; ERRMSG$
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
SELECT department, AVG(salary) as avg_salary FROM employees GROUP BY department ORDER BY avg_salary DESC;

PRINT
PRINT "4. High earners (salary > 70000):"
PRINT "=================================="
SELECT name, department, salary FROM employees WHERE salary > 70000 ORDER BY salary DESC;

PRINT
PRINT "5. Employee count by department:"
PRINT "================================"
SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department ORDER BY employee_count DESC;

PRINT
PRINT "Test completed successfully!"

REM Clean up - remove the test file
KILL "employees.csv"
PRINT "Cleaned up test file"

END