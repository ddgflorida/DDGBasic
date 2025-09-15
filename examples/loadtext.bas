' This script demonstrates loading a text file into a sqlite table


' --- Step 1: Load the data   ---
PRINT "Loading data from the first table in colleges.html..."
LOAD TEXT "c:\ddg\data\csv\example.csv" CREATE TABLE "example" OPTIONS "linenum=1"

IF ERR <> 0 THEN
    PRINT "An error occurred during the LOAD TEXT command:"
    PRINT ERRMSG$
    END
END IF
PRINT "Data loaded successfully."
PRINT

' --- Step 3: Display the results ---
PRINT "--- Florida Tennis Colleges Data ---"
SELECT * FROM example ORDER BY [_linenum];
DESCRIBE TABLE "example"
 


