REM --- Text File Reading Example ---
REM This program demonstrates writing a few lines to a standard text file
REM using PRINT #, and then reading it back line-by-line using a
REM WHILE...WEND loop with the EOF() function.

PRINT "--- Text File Example ---"
LET FILENAME$ = "logfile.txt"

REM Create and write to a text file
OPEN FILENAME$ FOR OUTPUT AS #1
PRINT #1, "Log started at " + TIME$
PRINT #1, "---"
PRINT #1, "First event: System initialized."
PRINT #1, "Second event: User logged in."
CLOSE #1

PRINT "Log file created. Now reading content:"
PRINT "--------------------------"

REM Open the file for reading
OPEN FILENAME$ FOR INPUT AS #1

REM Loop until the End-Of-File (EOF) is reached
WHILE NOT EOF(1)
    LINE INPUT #1, LINE$
    PRINT LINE$
WEND
CLOSE #1

PRINT "--------------------------"
PRINT "End of file."

END
