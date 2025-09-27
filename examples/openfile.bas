REM Write to file
OPEN "output.txt" FOR OUTPUT AS #1
PRINT #1, "Hello, World!"
PRINT #1, "Line 2"
CLOSE #1

REM Read from file
OPEN "output.txt" FOR INPUT AS #2
WHILE NOT EOF(2)
    LINE INPUT #2, line$
    PRINT line$
WEND
CLOSE #2

REM Append to file
n = FREEFILE
OPEN "log.txt" FOR APPEND AS #n
PRINT #n, DATE$; " "; TIME$; " - Event logged"
CLOSE #n

KILL "log.txt"

