REM SET THEME sets the four colours of COLOR; CLS paints the screen in them.
SET THEME "classic"
CLS
s$ = SAVESCREEN(1, 1, 1, 1)
IF INSTR(s$, CHR$(34) + " " + CHR$(34) + ",15,1]") = 0 THEN ERROR 1, "classic is white (15) on blue (1): " + s$
@ 2, 1 GET x$ PICTURE "@S3"
s$ = SAVESCREEN(2, 1, 2, 1)
IF INSTR(s$, ",0,3]") = 0 THEN ERROR 1, "classic fields are black (0) on cyan (3): " + s$
SET THEME "GREEN"
CLS
IF INSTR(SAVESCREEN(1, 1, 1, 1), ",10,0]") = 0 THEN ERROR 1, "green, in capitals too"
SET THEME "default"
CLS
IF INSTR(SAVESCREEN(1, 1, 1, 1), ",7,0]") = 0 THEN ERROR 1, "default"
PRINT "themes: all checks passed"
REM EXPECT: themes: all checks passed
SET THEME "plaid"
REM EXPECT: There is no theme called plaid. The themes are: default, classic, norton, green, amber, paper, mono.
