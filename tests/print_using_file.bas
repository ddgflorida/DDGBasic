REM PRINT #n, USING must write a line ending (unless the line ends with ;)
REM and produce the same text as PRINT USING on the console.
REM Any failed check raises an error (exit 1).
OPEN "print_using_file.txt" FOR OUTPUT AS #1
PRINT #1, USING "##.##"; 3.14159
PRINT #1, USING "Total: ###"; 42;
PRINT #1, " units"
PRINT #1, "plain line"
CLOSE #1

OPEN "print_using_file.txt" FOR INPUT AS #1
LINE INPUT #1, a$
LINE INPUT #1, b$
LINE INPUT #1, c$
CLOSE #1
KILL "print_using_file.txt"

IF a$ <> " 3.14" THEN ERROR 1, "line 1 was [" + a$ + "]"
IF b$ <> "Total:  42 units" THEN ERROR 1, "line 2 was [" + b$ + "]"
IF c$ <> "plain line" THEN ERROR 1, "line 3 was [" + c$ + "]"
PRINT "print_using_file: all checks passed"
