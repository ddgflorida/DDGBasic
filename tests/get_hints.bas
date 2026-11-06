REM GET ... HINT: the current field's hint is on the bottom line during READ; a field
REM without a hint shows what was there; READ puts the line back. Keys from the test runner.
CLS
@ 24, 1 SAY "Status line"
bottom$ = SAVESCREEN(24, 1, 24, 80)
seen1$ = "" : seen2$ = "" : seen3$ = ""
FUNCTION grab()
    IF seen1$ = "" THEN
        seen1$ = SAVESCREEN(24, 1, 24, 80)
    ELSEIF seen2$ = "" THEN
        seen2$ = SAVESCREEN(24, 1, 24, 80)
    ELSE
        seen3$ = SAVESCREEN(24, 1, 24, 80)
    END IF
END FUNCTION
ON KEY "F5" CALL grab
REM SAVESCREEN strings also hold the cursor; compare only the characters and colours
FUNCTION cells$(s$)
    cells$ = MID$(s$, INSTR(s$, "cells"))
END FUNCTION
name$ = "" : phone$ = "" : city$ = ""
@ 2, 2 SAY "Name : " GET name$ PICTURE "@S20" HINT "Type the full name"
@ 3, 2 SAY "Phone: " GET phone$ PICTURE "@R (999) 999-9999" HINT "Ten digits; the brackets are filled in"
@ 4, 2 SAY "City : " GET city$ PICTURE "@S20"
REM Keys: F5 "Ann" Enter F5 "5551234567" Enter F5 "Boston" Enter
READ
IF cells$(seen1$) = cells$(bottom$) OR cells$(seen2$) = cells$(bottom$) OR cells$(seen1$) = cells$(seen2$) THEN ERROR 1, "each hint should be on the bottom line"
IF cells$(seen3$) <> cells$(bottom$) THEN ERROR 1, "a field without a hint should show the line as it was"
IF cells$(SAVESCREEN(24, 1, 24, 80)) <> cells$(bottom$) THEN ERROR 1, "READ should put the bottom line back"
IF name$ <> "Ann" OR phone$ <> "5551234567" OR city$ <> "Boston" THEN ERROR 1, "values"
CLS
PRINT "get_hints: all checks passed"
REM EXPECT: get_hints: all checks passed
