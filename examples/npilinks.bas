url$ = "https://download.cms.gov/nppes/NPI_Files.html"
local_file$ = "npi_download_page.html"

PRINT "Downloading " + url$ + "..."

REM Step 2: Fetch the HTML content and save it to a local file.
FETCH url$ TO FILE local_file$

REM It's good practice to check if the download was successful.
IF NOT (ERR = 0 OR ERR = 200) THEN
    PRINT "Error: Could not download the file. " + ERRMSG$
    END
END IF

PRINT "Download successful to", local_file$," Parsing HTML links..."

REM Step 3: Use LOAD HTML LINKS to parse the file and create a table named 'npi_links'.
REM This command automatically creates the table with columns: source, text, and href.
LOAD HTML local_file$ CREATE TABLE npi_links OPTIONS "element_type=links"

PRINT "Table 'npi_links' created successfully."
PRINT 

REM Step 4: Query the new table to find the download links for the weekly data files.
PRINT "--- Found NPI Weekly Data File Links ---"
FOR rec in (SELECT * FROM npi_links WHERE href like '%diss%' ORDER BY href)
   print rec
NEXT

REM Step 5: Clean up the downloaded temporary HTML file.
PRINT 
PRINT "Cleaning up temporary file: " + local_file$
REM KILL local_file$

PRINT "Script finished."