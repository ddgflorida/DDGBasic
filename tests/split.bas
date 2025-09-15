REM --- SPLIT Pipe-Delimited String Example ---

PRINT "Splitting a pipe-delimited record..."

REM The source string with pipe '|' delimiters
record$ = "1024|ACTIVE|j.smith@example.com|2025-08-25"
PRINT record$
PRINT

REM Dimension a dynamic array to hold the results
DIM fields$ AS ARRAY

REM Split the record string into the array
fields$ = SPLIT(record$, "|")

REM Loop from the first element (0) to the upper bound of the array
FOR i = 0 TO UBOUND(fields$)
    REM Print the 1-based field number and its value
    PRINT "Field "; i + 1; ": "; fields$(i)
NEXT i

END