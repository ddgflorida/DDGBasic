REM 1. Analyze the raw data to check for issues
filename$ = "\ddg\data\csv\raw_sales.csv"
ANALYZE CSV filename$ OPTIONS "constraints=[State]:IN(CA,NY,FL)"

REM 2. Load and clean the data in a single step
REM - Skip the first 3 lines
REM - Trim all fields
REM - Standardize the 'State' column to uppercase
options$ = "header=true transform=trimall;State:upper;Status:upper"
LOAD CSV filename$ CREATE TABLE "sales" OPTIONS options$
DESCRIBE "sales"
SELECT * FROM sales ORDER BY 1;
REM 3. Perform a final, targeted cleanup using SQL
UPDATE sales SET status = substr(status,1,1) WHERE length(status)>1;
PRINT "Data cleaning complete."
SELECT * FROM sales ORDER BY 1 LIMIT 5;

END