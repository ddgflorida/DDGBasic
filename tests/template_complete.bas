REM A template field is either left empty or filled in completely: 9, A and N positions
REM need a character once anything is typed. Keys come from the test runner's STDIN.
COLOR 15, 1
CLS
phone$ = "" : zip$ = "" : code$ = ""
@ 3, 5 SAY "Phone: " GET phone$ PICTURE "(999) 999-9999"
@ 4, 5 SAY "Zip  : " GET zip$ PICTURE "99999"
@ 5, 5 SAY "Code : " GET code$ PICTURE "AA-999" MESSAGE "Two letters and three digits"
REM Keys: "555123" Enter (refused: half a phone number), "4567" Enter, Enter (an empty zip
REM is fine), "xy12" PgDn (refused), "3" PgDn (saved)
READ
COLOR 7, 0
CLS
IF phone$ <> "(555) 123-4567" THEN ERROR 1, "phone: [" & phone$ & "]"
IF zip$ <> "" THEN ERROR 1, "zip: [" & zip$ & "]"
IF code$ <> "xy-123" THEN ERROR 1, "code: [" & code$ & "]"
PRINT "template_complete: all checks passed"
REM EXPECT: Fill in the whole field, or leave it empty
REM EXPECT: Two letters and three digits
REM EXPECT: template_complete: all checks passed
