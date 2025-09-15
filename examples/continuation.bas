REM Test line continuation with underscore
PRINT "Testing line continuation..."

REM Simple continuation
PRINT "This is a long message that spans " _
      + "multiple lines using continuation"

REM Continuation in expressions
x = 10 + _
    20 + _
    30
PRINT "x = "; x

REM Continuation with strings containing underscores
filename$ = "data_file.txt"
PRINT "File: " _
      + filename$ _
      + " loaded"

REM Continuation should NOT work in comments
REM This underscore should be ignored _
PRINT "After comment with underscore"

REM Continuation should NOT work in strings
message$ = "This underscore should stay: _"
PRINT "Message: "; message$

REM Continuation with IF statements
PRINT "Test IF STATEMENT"
IF x > 50 _
   AND filename$ <> "" _
   THEN
    PRINT "Complex condition met"
END IF
PRINT "TEST SQL STRING"
REM Continuation with backtick strings
query$ = `SELECT * FROM table ` _
         + `WHERE id > 0`
PRINT "Query: "; query$

PRINT "All tests complete"
END