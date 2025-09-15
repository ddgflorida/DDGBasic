' This script demonstrates downloading an HTML page,
' parsing a table from it, and loading it into the database.

' --- Step 1: Download the webpage ---
PRINT "Fetching HTML from the web..."
FETCH "https://www.tournamentmaps.com/florida-tennis-colleges.htm" TO FILE "colleges.html"

' A good practice is to check if the download was successful (HTTP status 200).
IF ERR <> 200 THEN
    PRINT "Failed to download the webpage. Error code:"; ERR
    END
END IF
PRINT "Download complete. File saved as colleges.html."
PRINT

' --- Step 2: Load the data from the HTML table ---
PRINT "Loading data from the first table in colleges.html..."
' The command finds the first table (table_index=0) and uses its first row
' as the column names (header=true).
LOAD HTML "colleges.html" CREATE TABLE colleges OPTIONS "header=true,table_index=0,linenum=1"

IF ERR <> 0 THEN
    PRINT "An error occurred during the LOAD HTML command:"
    PRINT ERRMSG$
    END
END IF
PRINT "Data loaded successfully."
PRINT

' --- Step 3: Display the results ---
PRINT "--- Florida Tennis Colleges Data ---"
SELECT * FROM colleges ORDER BY [_linenum];
DESCRIBE TABLE "colleges"
REM KILL "colleges.html"


