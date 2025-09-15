REM --- Employee Report Generator ---
REM This script demonstrates creating an HTML report from a database
REM and opening it with the BROWSER command.

REM 1. Set up an in-memory database with some sample data
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"
CREATE TABLE employees (id INTEGER, name TEXT, title TEXT, department TEXT);
INSERT INTO employees VALUES (101, 'Alice Williams', 'Software Engineer', 'Technology');
INSERT INTO employees VALUES (102, 'Bob Johnson', 'Project Manager', 'Management');
INSERT INTO employees VALUES (103, 'Charlie Brown', 'Data Analyst', 'Analytics');
INSERT INTO employees VALUES (104, 'Diana Miller', 'UX Designer', 'Product');

REM 2. Prepare to write the HTML file
LET report_file$ = "employee_report.html"
SET OUTPUT FILE report_file$ FORMAT HTML
SELECT id, name, title, department FROM employees ORDER BY name;

PRINT "Report '" + report_file$ + "' generated successfully."

REM 6. Use the BROWSER command to open the local HTML file
LET full_path$ = "file:///" + CURDIR$() + "/" + report_file$
BROWSER full_path$
