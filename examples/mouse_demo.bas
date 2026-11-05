REM Mouse demo: a tiny paint program. Click to draw, right-click to erase,
REM turn the wheel to change colour, Esc to quit. INKEY$ returns CLICK, RCLICK,
REM WHEELUP and WHEELDOWN for the mouse; MOUSEROW and MOUSECOL give the position.
COLOR 15, 1
CLS
BOX 1, 1, 23, 80, "Paint (Esc quits)"
colour = 14 : count = 0
DO
    k$ = INKEY$(0)
    IF k$ = "CLICK" AND MOUSEROW > 1 AND MOUSEROW < 23 THEN
        COLOR colour, 1
        @ MOUSEROW, MOUSECOL SAY "*"
        count = count + 1
    ELSEIF k$ = "RCLICK" THEN
        COLOR 15, 1
        @ MOUSEROW, MOUSECOL SAY " "
    ELSEIF k$ = "WHEELUP" OR k$ = "WHEELDOWN" THEN
        colour = MOD(colour, 15) + 1
        COLOR 15, 1
        @ 24, 2 SAY "Colour" & STR$(colour) & "  "
    END IF
LOOP UNTIL k$ = CHR$(27)
COLOR 7, 0
CLS
PRINT "You drew"; count; " stars."
REM EXPECT: You drew 3 stars.
