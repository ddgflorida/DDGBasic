REM ---
REM DDGBasic program to analyze the NPPES NPI Monthly Data file.
REM This script uses the ANALYZE CSV command to generate a detailed
REM statistical report on the first 100,000 data records.
REM ---

PRINT "--- Starting NPPES File Analysis (first 100,000 records) ---"
PRINT

REM --- Configuration ---
REM Set the path to your local copy of the NPPES CSV file.
nppes_file$ = "C:\DDG\NPI\NPPES_Data_Dissemination_July_2025_V2\npidata_pfile_20050523-20250713.csv"

REM --- Define Validation Constraints ---
REM We build the constraints string in parts for readability.

REM 1. NPI is always required and must be 10 digits.
constraints$ = "[NPI]:REQUIRED;[NPI]:ISDIGITS;[NPI]:MINLENGTH(10);[NPI]:MAXLENGTH(10);"

REM 2. Entity Type Code must be 1 or 2 (if it's not empty).
constraints$ = constraints$ + "[Entity Type Code]:IN(1,2);"

REM 3. State must be exactly 2 characters (if it's not empty).
constraints$ = constraints$ + "[Provider Business Mailing Address State Name]:MINLENGTH(2);[Provider Business Mailing Address State Name]:MAXLENGTH(2);"

REM 4. Postal Code must be 5 or 9 digits (if it's not empty).
constraints$ = constraints$ + "[Provider Business Mailing Address Postal Code]:REGEX(^\d{5}(?:-?\d{4})?$);"

REM 5. Date fields must be in MM/DD/YYYY format (if not empty).
constraints$ = constraints$ + "[Provider Enumeration Date]:ISDATE(MM/DD/YYYY);[Last Update Date]:ISDATE(MM/DD/YYYY)"

REM --- Construct the Final OPTIONS String ---
REM We combine the header setting with our constraints and a limit of 100,000 records.
REM (The full file has millions of rows; raise the limit to analyze more of it.)
options$ = `header=true limit=100000 constraints="` + constraints$ + `"`

PRINT "Analyzing file: "; nppes_file$
PRINT "Using options: "; options$
PRINT

REM --- Run the Analysis ---
REM This will print a detailed report to the console for the first 100,000 records.
DIM report$ AS HASH
ANALYZE CSV nppes_file$ INTO report$ OPTIONS options$
REM Note that if you remove INTO report$ then we get default output for ANALYZE CSV

IF ERR <> 0 THEN
    PRINT "An error occurred during analysis:"
    PRINT ERRMSG$
END IF
PRINT report$
PRINT
PRINT "--- Analysis Complete ---"
END