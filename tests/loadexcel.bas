REM ---
REM Example: Load data from an Excel .xls file into a SQLite table
REM ---

PRINT "--- Starting Excel Load Process ---"
PRINT

REM --- Configuration ---
REM Set the path to your Excel .xls file.
excel_file$ = "c:\ddg\data\excel\example.xlsx"

REM --- Database Setup ---
DATABASE OPEN ":memory:"

REM --- Load the Excel File ---
PRINT "Loading data from "; excel_file$; "..."
REM This creates a new table named 'excel_data' using the first sheet.
REM It assumes the first row in the sheet is the header.
LOAD EXCEL excel_file$ CREATE TABLE "excel_data" OPTIONS "header=true"

IF ERR <> 0 THEN
    PRINT "An error occurred during the Excel load:"
    PRINT ERRMSG$
    END
END IF

PRINT
PRINT "--- Verifying Loaded Data (first 5 rows) ---"
SELECT * FROM excel_data LIMIT 5;

PRINT
PRINT "--- Process Complete ---"
DATABASE CLOSE
END