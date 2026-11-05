REM @ ... BUTTON and BUTTON$: buttons in a READ form. Keys come from the test runner.
REM Failed checks raise errors.
COLOR 15, 1 : CLS
name$ = "old" : qty = 1
REM Keys: Ctrl-Y "new" Enter, "5" Enter (onto Save), Enter (press Save)
GOSUB form
IF BUTTON$ <> "Save" OR name$ <> "new" OR qty <> 5 THEN ERROR 1, "Save: " & BUTTON$ & " " & name$
IF LASTKEY$ <> CHR$(13) THEN ERROR 1, "LASTKEY$ after a button"
REM Keys: Ctrl-Y "zzz" Tab Tab (Save) Tab (Cancel) Enter: a CANCEL button puts the old values back
GOSUB form
IF BUTTON$ <> "Cancel" OR name$ <> "new" THEN ERROR 1, "Cancel: " & BUTTON$ & " " & name$
REM Keys: Ctrl-Y "x" Esc: no button
GOSUB form
IF BUTTON$ <> "" OR name$ <> "new" THEN ERROR 1, "Esc: [" & BUTTON$ & "]"
REM Keys: Ctrl-Y Enter (refused by VALID) "ok" Tab x6 (Save, Cancel, wrap to Name, Qty, Save) Space
GOSUB form
REM EXPECT: Name is required
IF BUTTON$ <> "Save" OR name$ <> "ok" THEN ERROR 1, "VALID, wrap and Space: " & BUTTON$ & " " & name$
REM A form with only buttons. Keys: Right Enter
@ 8, 5 BUTTON "Yes"
@ 8, 13 BUTTON "No"
READ
IF BUTTON$ <> "No" THEN ERROR 1, "buttons only: " & BUTTON$
COLOR 7, 0
CLS
PRINT "form_buttons: all checks passed"
REM EXPECT: form_buttons: all checks passed
END
form:
    @ 3, 5 SAY "Name: " GET name$ PICTURE "@S20" VALID name$ <> "" MESSAGE "Name is required"
    @ 4, 5 SAY "Qty : " GET qty
    @ 6, 5 BUTTON "Save"
    @ 6, 15 BUTTON "Cancel" CANCEL
    READ
    RETURN
