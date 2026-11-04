REM 1. Analyze the raw data to check for issues
filename$ = "\ddg\data\csv\raw_sales.csv"
options$ = "constraints=[State]:IN(CA,NY,FL)"
PRINT "1. Analyze ";filename$;" using options:";options$
PRINT
ANALYZE CSV filename$ OPTIONS options$

PRINT
PRINT "2. Load and clean the data in a single step"
PRINT " - Skip the first 3 lines"
PRINT " - Trim all fields"
PRINT " - Standardize the 'State' column to uppercase"
options$ = "header=true transform=trimall;State:upper;Status:upper"
PRINT " Run LOAD CSV file to table sales"; " using options "; options$
LOAD CSV filename$ CREATE TABLE "sales" OPTIONS options$
PRINT
PRINT "Description of sales:"
DESCRIBE "sales"

PRINT
PRINT "Show data from table sales"
SELECT * FROM sales ORDER BY 1;

REM 3. Perform a final, targeted cleanup using SQL
PRINT
PRINT "Change status via an UPDATE statement: UPDATE sales SET status = substr(status,1,1) WHERE length(status)>1;"
UPDATE sales SET status = substr(status,1,1) WHERE length(status)>1;
PRINT "Data cleaning complete."
SELECT * FROM sales ORDER BY 1 LIMIT 5;

END