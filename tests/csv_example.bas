REM --- CSV File Handling Example ---
REM This program demonstrates writing data to a CSV file using WRITE #
REM and then reading it back using a FOR...IN CSV loop.

PRINT "--- CSV Example ---"
LET FILENAME$ = "inventory.csv"

REM Open the file for writing. This will create or overwrite the file.
OPEN FILENAME$ FOR OUTPUT AS #1

PRINT "Writing data to"; FILENAME$

REM Use WRITE # to output CSV-formatted lines.
REM Note that "Monitors, Widescreen" will be correctly quoted.
WRITE #1, 101, "Laptop", 15
WRITE #1, 102, "Monitors, Widescreen", 22
WRITE #1, 103, "Keyboard", 50
CLOSE #1

PRINT "Finished writing. Now reading data back."
PRINT "--------------------------"

REM The loop automatically handles parsing and stops at the end of the file.
FOR rec IN CSV (FILENAME$)
    PRINT "ID:"; rec(1), "Product:"; rec(2), "Qty:"; rec(3)
NEXT

PRINT "--------------------------"
PRINT "Finished reading CSV."

END