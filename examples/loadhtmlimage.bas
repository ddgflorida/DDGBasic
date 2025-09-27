REM This script demonstrates downloading an HTML page,
REM parsing a table from it, and loading it into the database.

REM --- Step 1: Download the webpage ---
PRINT "Fetching HTML from the web..."
FETCH "https://www.tournamentmaps.com/" TO FILE "images.html"

REM A good practice is to check if the download was successful (HTTP status 200).
IF ERR <> 200 THEN
    PRINT "Failed to download the webpage. Error code:"; ERR
    END
END IF
PRINT "Download complete. File saved as images.html."
PRINT

REM --- Step 2: Load the data from the HTML table ---
PRINT "Loading image references in images.html..."
REM The command finds <img> tags in an html table.
LOAD HTML IMAGES "images.html" CREATE TABLE college_images
IF ERR <> 0 THEN
    PRINT "An error occurred during the LOAD HTML IMAGES command:"
    PRINT ERRMSG$
    END
END IF
PRINT "Images loaded successfully in table college_images."
PRINT

REM --- Step 3: Display the results ---
PRINT "--- Florida Tennis images Data ---"
SELECT * FROM college_images;
PRINT
PRINT "Table college_images CREATE TABLE statement:"
DESCRIBE TABLE "college_images"
KILL "images.html"


