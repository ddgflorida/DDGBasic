REM SET STYLE "modern" (the default) and "classic"; an unknown name is an error
SET STYLE "classic"
COLOR 15, 1
CLS
BOX 2, 2, 5, 30, "Classic" DOUBLE
SET STYLE "Modern"
CLS
BOX 2, 2, 5, 30, "Modern"
ON ERROR GOTO caught
msg$ = ""
SET STYLE "neon"
ON ERROR GOTO 0
COLOR 7, 0
CLS
IF INSTR(msg$, "There is no style called neon") = 0 THEN ERROR 1, "unknown style: " & msg$
PRINT "set_style: all checks passed"
REM EXPECT: ╔═
REM EXPECT: ╭─
REM EXPECT: set_style: all checks passed
END
caught:
    msg$ = ERRMSG$
    RESUME NEXT
