REM --- Convert CSV to JSON with Additional Form Fields ---
URL$ = "https://www.convertcsv.io/api/v1/csv2json"
REM The API token comes from the environment, so it never sits in the source:
REM   set CONVERTCSV_TOKEN=your-token        (Windows)
REM   export CONVERTCSV_TOKEN=your-token     (macOS/Linux)
TOKEN$ = ENVIRON$("CONVERTCSV_TOKEN")
IF TOKEN$ = "" THEN
    PRINT "Set the CONVERTCSV_TOKEN environment variable to your convertcsv.io API token."
    END
END IF
INPUT_FILENAME$ = "INVENTORY.csv"
OUTPUT_FILENAME$ = "INVENTORY.json"
RESPONSE$ = ""

REM --- Create a dummy INVENTORY.CSV for the test ---
PRINT "Creating File "; INPUT_FILENAME$
OPEN INPUT_FILENAME$ FOR OUTPUT AS #1
PRINT #1, "ID,Name,Quantity"
PRINT #1, "101,Super Gadget,50"
PRINT #1, "102,Mega Widget,75"
CLOSE #1
PRINT "--------------------------------"
SHELL "type " + INPUT_FILENAME$
PRINT "--------------------------------"

REM --- Set up Headers ---
DIM Headers AS HASH
Headers("Authorization") = "Token " + TOKEN$

REM --- Set up the POST Payload with form fields ---
DIM Payload AS HASH
Payload("array") = "Y"
Payload("encoding") = "UTF-8"
Payload("fields") = "1-3"

REM --- Perform the FETCH with payload, file, and headers ---
PRINT "Uploading INVENTORY.CSV with form data for CSV to JSON conversion..."
FETCH URL$ POST Payload() USING FILE "infile" = INPUT_FILENAME$ USING HEADERS Headers() INTO RESPONSE$

PRINT "HTTP Status (ERR):"; ERR

IF ERR = 200 THEN
    PRINT "Success! Saving output to "; OUTPUT_FILENAME$
    FN = FREEFILE
	PRINT "Using FREEFILE VALUE OF ";FN
    OPEN OUTPUT_FILENAME$ FOR OUTPUT AS #FN
	PRINT "PRINTING TO #FN"
    PRINT #FN, RESPONSE$
	PRINT "PRINTED RESPONSE, Closing #FN";FN
    CLOSE
	PRINT "------------------------------------"
	SHELL "type " + OUTPUT_FILENAME$
	PRINT "------------------------------------"
ELSE
    PRINT "Error converting file."
    PRINT "Server response:"
    PRINT RESPONSE$
END IF

REM --- Clean up the dummy file ---
PRINT  
PRINT "Removing input file "; INPUT_FILENAME$
KILL INPUT_FILENAME$
PRINT "Removing outpout file "; OUTPUT_FILENAME$
KILL OUTPUT_FILENAME$
PRINT "Done"
