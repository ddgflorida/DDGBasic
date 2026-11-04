REM A label is a name followed by ':' at the start of a line. A name followed by
REM ':' elsewhere on a line (a = b : c = b, GOSUB sub : ...) is not a label.
REM Any failed check raises an error (exit 1).
b = 5
a = b : c = b
IF a <> 5 OR c <> 5 THEN ERROR 1, "multi-statement assignment line"
calls = 0
GOSUB count_call : GOSUB count_call
IF calls <> 2 THEN ERROR 1, "GOSUB ... : GOSUB on one line, calls = " + STR$(calls)
x = 1
again: x = x + 1 : IF x < 3 THEN GOTO again
IF x <> 3 THEN ERROR 1, "label followed by statements on the same line, x = " + STR$(x)
PRINT "labels: all checks passed"
END

count_call:
  calls = calls + 1
  RETURN
