REM DbBasic script to download, transform, and load a remote CSV

PRINT "--- Starting Process ---"

REM Step 1: Fetch the CSV data from the URL.
PRINT "1. Fetching CSV data from URL..."
url$ = "https://raw.githubusercontent.com/cisagov/dotgov-data/main/current-full.csv"
FETCH url$ TO FILE "dotgov.csv"
IF ERR <> 200 THEN
    PRINT "Error: Failed to download file. Status code:"; ERR
    PRINT ERRMSG$
    END
END IF
PRINT "-> Download successful."
PRINT

REM --- TEST 1: Load CSV into SQLite with Transformations ---
db_file$ = "dotgov.db"
PRINT "2. Loading CSV into SQLite database '";db_file$;"' with transformations..."
DATABASE OPEN db_file$

REM Define options for trimming all fields and uppercasing the 'State' column
options_db$ = "header=true batchsize=5 transform=trimall;State:upper;City:upper"
LOAD CSV "dotgov.csv" CREATE TABLE "domains" OPTIONS options_db$
IF ERRMMSG$ <> "" THEN PRINT ERRMSG$
PRINT "-> Load to database complete."
PRINT

PRINT "3. Verifying transformed data in database (first 5 rows):"
SELECT "Domain Name", City, State FROM domains WHERE State = 'NY' LIMIT 5;
PRINT


REM --- FINAL CLEANUP ---
PRINT "6. Cleaning up temporary files..."
DATABASE CLOSE
KILL "dotgov.csv"
KILL "dotgov.json"
PRINT "-> Done."

END
