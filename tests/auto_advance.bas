REM SET AUTOADVANCE: filling a field moves to the next one, and filling the last field
REM ends READ. VALID still applies. Keys come from the test runner. Failed checks raise errors.
SET AUTOADVANCE ON
state$ = "" : zip$ = "" : phone$ = ""
@ 2, 1 SAY "State: " GET state$ PICTURE "!!"
@ 3, 1 SAY "Zip  : " GET zip$   PICTURE "99999" VALID LEFT$(zip$, 1) <> "0"
@ 4, 1 SAY "Phone: " GET phone$ PICTURE "(999) 999-9999"
REM Keys: "ca" "01234" (refused by VALID) Ctrl-Y "90210" "5551234567" -- no Tab or Enter at all
READ
IF state$ <> "CA" THEN ERROR 1, "state: " & state$
IF zip$ <> "90210" THEN ERROR 1, "zip: " & zip$
IF phone$ <> "(555) 123-4567" THEN ERROR 1, "phone: " & phone$
IF LASTKEY$ <> CHR$(13) THEN ERROR 1, "READ should end after the last field fills"

REM With AUTOADVANCE OFF (the default) the cursor stays in a full field until Enter or Tab
SET AUTOADVANCE OFF
a$ = "" : b$ = ""
@ 6, 1 SAY "A: " GET a$ PICTURE "!!"
@ 7, 1 SAY "B: " GET b$ PICTURE "!!"
REM Keys: "xyz" Tab "q" Enter Enter
READ
IF a$ <> "XZ" THEN ERROR 1, "a$ should keep the cursor in the full field: " & a$
IF b$ <> "Q" THEN ERROR 1, "b$: " & b$
LOCATE 10, 1
PRINT "auto_advance: all checks passed"
REM EXPECT: auto_advance: all checks passed
