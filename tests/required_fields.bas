REM REQUIRED fields, @L, and the check of every field's rules when the form is saved,
REM visited or not. REQUIRED is checked only on saving; VALID also going forward.
REM Keys come from the test runner's STDIN.
COLOR 15, 1
CLS
name$ = "" : email$ = "" : age = 0 : agree = 0 : limit = 500
@ 3, 5 SAY "Name : " GET name$ PICTURE "@S20" REQUIRED
@ 4, 5 SAY "Email: " GET email$ PICTURE "@L" HINT "lower case"
@ 5, 5 SAY "Age  : " GET age PICTURE "999" REQUIRED MESSAGE "Age is needed"
@ 6, 5 SAY "Agree: " GET agree CHECKBOX REQUIRED
@ 7, 5 SAY "Limit: " GET limit PICTURE "9999" VALID limit <= 100 MESSAGE "Too big"
@ 9, 5 BUTTON "Save"
REM Keys: Tab on the empty Name (allowed: REQUIRED waits for the save), "ANN@X.COM",
REM Shift-Tab back to Name, "Ann", PgDn (Age is required: the cursor goes there),
REM "30" PgDn (Agree is not ticked), Space PgDn (Limit's VALID fails: the cursor goes there),
REM "200" Enter (refused going forward), Shift-Tab (going back is allowed), PgDn (Limit
REM still fails), "50" PgDn (saved)
READ
COLOR 7, 0
CLS
IF name$ <> "Ann" THEN ERROR 1, "name: " & name$
IF email$ <> "ann@x.com" THEN ERROR 1, "@L: " & email$
IF age <> 30 THEN ERROR 1, "age: " & STR$(age)
IF NOT agree THEN ERROR 1, "agree"
IF limit <> 50 THEN ERROR 1, "limit: " & STR$(limit)
PRINT "required_fields: all checks passed"
REM EXPECT: This field is required
REM EXPECT: Age is needed
REM EXPECT: Too big
REM EXPECT: required_fields: all checks passed
