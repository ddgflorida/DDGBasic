REM Shift-Tab goes back a field, and from the first field wraps round to the last.
REM Keys come from the test runner's STDIN.
COLOR 15, 1
CLS
a$ = "" : b$ = "" : c$ = ""
@ 3, 5 SAY "A: " GET a$ PICTURE "@S10"
@ 4, 5 SAY "B: " GET b$ PICTURE "@S10"
@ 5, 5 SAY "C: " GET c$ PICTURE "@S10"
REM Keys: Shift-Tab (wraps to C) "c" Shift-Tab (B) "b" Shift-Tab (A) "a" Enter Enter Enter
READ
COLOR 7, 0
CLS
IF a$ <> "a" OR b$ <> "b" OR c$ <> "c" THEN ERROR 1, "Shift-Tab order: [" & a$ & "|" & b$ & "|" & c$ & "]"
PRINT "back_tab: all checks passed"
REM EXPECT: back_tab: all checks passed
