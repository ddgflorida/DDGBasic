REM Programs read the same with LF, CRLF or CR line endings, with quotes in REM lines
REM (the runner's own file can be checked out either way)
cr$ = CHR$(13)
lf$ = CHR$(10)

REM 1. Program text built with each kind of line ending, run with EVAL
DIM endings AS HASH
endings("LF") = lf$
endings("CRLF") = cr$ & lf$
endings("CR") = cr$
FOR EACH kind$ IN HASH endings
    nl$ = endings(kind$)
    result$ = ""
    EVAL "REM it's a quote in a REM" & nl$ & _
         "x$ = ""a"" & _" & nl$ & "     ""b""" & nl$ & _
         "IF x$ = ""ab"" THEN" & nl$ & "    result$ = ""ok""" & nl$ & "END IF" & nl$
    IF result$ <> "ok" THEN ERROR 1, "EVAL with " & kind$ & ": [" & result$ & "]"
NEXT

REM 2. The same program saved with CRLF and with CR, then RUN
program$ = "REM don't stop here" & lf$ & "OPEN ""le_out.txt"" FOR OUTPUT AS #1" & lf$ & _
           "PRINT #1, ""ran""" & lf$ & "CLOSE #1" & lf$
FOR EACH kind$ IN HASH endings
    OPEN "le_prog.bas" FOR OUTPUT AS #1
    PRINT #1, REPLACE$(program$, lf$, endings(kind$));
    CLOSE #1
    IF FILE_EXISTS("le_out.txt") THEN KILL "le_out.txt"
    RUN "le_prog.bas"
    IF NOT FILE_EXISTS("le_out.txt") THEN ERROR 1, "RUN with " & kind$
NEXT

PRINT "line_endings: all checks passed"
REM EXPECT: line_endings: all checks passed
