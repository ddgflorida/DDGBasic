REM --- Test REGEX, ISDIGITS, and LENGTH constraints ---

REM Step 1: Create a sample CSV file with invalid data
OPEN "zips.csv" FOR OUTPUT AS #1
PRINT #1, "City,State,ZIPCODE"
PRINT #1, "New York,NY,10001"
PRINT #1, "Beverly Hills,CA,90210"
PRINT #1, "Boston,MAS,02116-4605" ' Invalid State (too long)
PRINT #1, "Miami,F,3310"         ' Invalid State (too short)
PRINT #1, "Chicago,IL,ABCDE"      ' Invalid ZIP (not digits)
CLOSE #1

PRINT "--- Analyzing zips.csv ---"
PRINT

REM Step 2: Run the analysis with all constraints
options$ = "header=true constraints=[ZIPCODE]:ISDIGITS;[ZIPCODE]:REGEX(^\d{5}$);[State]:MINLENGTH(2);[State]:MAXLENGTH(2)"
ANALYZE CSV "zips.csv" OPTIONS options$

REM --- Cleanup ---
KILL "zips.csv"

END
