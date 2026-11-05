REM END in a RUN child returns to the caller; END in the main program (here inside
REM a loop) stops the program. Any failed check raises an error (exit 1).
REM EXPECT: back in the caller after RUN
REM EXPECT: end_statement: all checks passed
RUN "helpers/end_child.bas"
IF ERR <> 0 THEN ERROR 1, "RUN child failed: " + ERRMSG$
PRINT "back in the caller after RUN"
FOR i = 1 TO 3
  IF i = 2 THEN
    PRINT "end_statement: all checks passed"
    END
  END IF
NEXT
ERROR 1, "END inside a loop did not stop the program"
