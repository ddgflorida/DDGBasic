REM --- This program reads a CSV file and converts it to a JSON Lines file ---

REM --- 1. Create a sample CSV file to use as input ---
OPEN "input.csv" FOR OUTPUT AS #1
PRINT #1, "user_id,first_name,last_name"
PRINT #1, "1,John,Doe"
PRINT #1, "2,Jane,Smith"
PRINT #1, "3,Peter,Jones"
CLOSE #1

PRINT "Created sample file: input.csv"
PRINT ""

REM --- 2. Open the destination file for the JSON Lines output ---
OPEN "output.jsonl" FOR OUTPUT AS #2

PRINT "Processing CSV and writing to output.jsonl..."

REM --- 3. Iterate through the CSV file, treating each row as a record ---
FOR rec IN CSV("input.csv") OPTIONS "header=true"
    ' Convert the record (which is a HASH) into a compact JSON string.
    ' We use the "LOWERCASE_KEYS" option to get a standard snake_case output.

    json_line$ = JSON_SERIALIZE$(rec, 0, "LOWERCASE_KEYS")

    ' Write the compact JSON string as a single line to the output file.
    PRINT #2, json_line$

NEXT

CLOSE #2

PRINT "Conversion complete."
PRINT

REM --- 4. (Optional) Display the contents of the new file for verification ---
PRINT "--- Contents of output.jsonl ---"
READ FILE "output.jsonl" INTO file_contents$
PRINT file_contents$

KILL "input.csv"
KILL "output.jsonl"
END