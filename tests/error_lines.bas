REM Error messages give the line where the error is: after END IF and END FUNCTION (joined
REM keywords) and after lines joined with _ . Each error is caught and its message checked.
ON ERROR GOTO caught
expected = 0
IF 1 = 1 THEN
    x = 1
END IF
IF 1 = 1 THEN
    x = 1
END IF
IF 1 = 1 THEN
    x = 1
END IF
IF 1 = 1 THEN
    x = 1
END IF
IF 1 = 1 THEN
    x = 1
END IF
IF 1 = 1 THEN
    x = 1
END IF
IF 1 = 1 THEN
    x = 1
END IF
IF 1 = 1 THEN
    x = 1
END IF
IF 1 = 1 THEN
    x = 1
END IF
IF 1 = 1 THEN
    x = 1
END IF
FUNCTION twice(n)
    twice = n * 2
END FUNCTION
y = 1 + _
    2 + _
    3
expected = 42
PRINT FOO(1)
PRINT "error_lines: all checks passed"
REM EXPECT: error_lines: all checks passed
END
caught:
    IF INSTR(ERRMSG$, "at line " + LTRIM$(STR$(expected)) + ",") = 0 THEN
        PRINT "wrong line: expected "; expected; " in "; ERRMSG$
        END
    END IF
    RESUME NEXT
