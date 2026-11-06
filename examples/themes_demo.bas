REM Themes demo: the same screen in each colour theme. Pick a theme from the menu;
REM Esc ends. In a program, SET THEME "classic" (then CLS) is all it takes.
DIM themes$(6)
themes$(0) = "Default" : themes$(1) = "Classic" : themes$(2) = "Norton" : themes$(3) = "Green"
themes$(4) = "Amber" : themes$(5) = "Paper" : themes$(6) = "Mono"
theme$ = "Classic"
DO
    SET THEME theme$
    CLS
    BOX 2, 1, 23, 80, "THEME: " & UCASE$(theme$) DOUBLE
    BOX 4, 30, 15, 74, "Customer" SHADOW
    name$ = "Acme Corp" : phone$ = "5551234567" : state$ = "FL" : active = -1
    @ 6, 33 SAY "Name   : " GET name$ PICTURE "@S25"
    @ 7, 33 SAY "Phone  : " GET phone$ PICTURE "@R (999) 999-9999"
    @ 8, 33 SAY "State  : " GET state$ LIST "CA,FL,NY,TX"
    @ 9, 33 SAY "Active : " GET active CHECKBOX
    @ 12, 33 BUTTON "Save"
    @ 12, 43 BUTTON "Cancel"
    @ 24, 2 SAY "Pick a theme; Esc ends.   SET THEME " & CHR$(34) & LCASE$(theme$) & CHR$(34)
    n = MENU(4, 4, themes$)
    IF n > 0 THEN theme$ = themes$(n - 1)
LOOP UNTIL n = 0
SET THEME "default"
CLS
PRINT "Last theme: "; LCASE$(theme$)
REM EXPECT: Last theme: green
