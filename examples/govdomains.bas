REM DbBasic script to download a remote CSV and load it into SQLite

PRINT "--- Starting Process ---"

REM Step 1: Fetch the CSV data from the URL into a variable.
PRINT "1. Fetching CSV data from URL..."
url$ = "https://raw.githubusercontent.com/cisagov/dotgov-data/main/current-full.csv"
FETCH url$ INTO csv_data$

REM The FETCH command puts the HTTP status code in the ERR variable.
REM A status of 200 means the download was successful.
IF ERR <> 200 THEN
    PRINT "Error: Failed to download file. Status code:"; ERR
    END
END IF
PRINT "-> Download successful."
PRINT

REM Step 2: Save the downloaded data to a temporary local file.
PRINT "2. Saving data to a local file..."
temp_file$ = "dotgov.csv"
OPEN temp_file$ FOR OUTPUT AS #1
PRINT #1, csv_data$
CLOSE #1
PRINT "-> Data saved to '"; temp_file$; "'."
SHELL "head -5 " + temp_file$
PRINT

REM Step 3: Open a database and load the local CSV file into a new table.
PRINT "Step 3: Open database and load the local CSV file into a table."
db_file$ = "dotgov.db"
IF FILE_EXISTS(db_file$) THEN
    KILL db_file$
END IF
PRINT "3. Loading CSV into SQLite database ";db_file$;" table 'domains'..."
DATABASE OPEN db_file$

REM The 'header=true' option tells the interpreter that the csv file has headers
REM row of the CSV as the column names for the new table.
PRINT "Load csv file ";temp_file$;" into table DOMAINS, database: ";db_file$
LOAD CSV temp_file$ CREATE "domains" OPTIONS "header=true"
IF ERRMSG$ <> "" THEN PRINT ERRMSG$
PRINT "-> Load complete."
PRINT
PRINT "After Load - Counting..."
LET cnt = (SELECT COUNT(*) FROM domains)
PRINT "Number of rows loaded into database table ";"domains"; " is "; cnt
PRINT
REM Step 4: Run a query to verify the data was loaded correctly.
PRINT "4. Verifying data (first 5 rows):"
SELECT "Domain Name", City, State FROM domains LIMIT 5;
PRINT

REM Step 5: Clean up by closing the database and deleting the temporary file.
PRINT "5. Cleaning up..."
DATABASE CLOSE
KILL temp_file$
PRINT "-> Done."

END