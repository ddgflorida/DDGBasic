REM EDIT TEXT: the memo editor. Keys come from the test runner. Failed checks raise errors.
COLOR 15, 1 : CLS
notes$ = "first line" + CHR$(10) + "second line"
before$ = SAVESCREEN()
REM Keys: End " ok" Enter "third" Down Up Home Del Del Ctrl-W
EDIT TEXT notes$ AT 3, 5, 12, 50 TITLE "Notes"
IF notes$ <> "first line ok" + CHR$(10) + "ird" + CHR$(10) + "second line" THEN ERROR 1, "edit and save: " & notes$
IF LASTKEY$ <> CHR$(23) THEN ERROR 1, "LASTKEY$ after Ctrl-W"
IF SAVESCREEN() <> before$ THEN ERROR 1, "EDIT TEXT did not restore the screen"
kept$ = notes$
REM Keys: "zz" Esc, Enter (No: keep editing), Ctrl-Y Esc, Right Enter (Yes: discard)
EDIT TEXT notes$ AT 3, 5, 12, 50
IF notes$ <> kept$ THEN ERROR 1, "Esc should discard the changes"
IF LASTKEY$ <> CHR$(27) THEN ERROR 1, "LASTKEY$ after a cancel"
REM Keys: Ctrl-Y (delete the first line) F10 (save)
EDIT TEXT notes$ AT 3, 5, 12, 50
IF notes$ <> "ird" + CHR$(10) + "second line" THEN ERROR 1, "Ctrl-Y and F10: " & notes$
REM A hash field; Tab inserts spaces. Keys: End Tab "y" Ctrl-W
rec.memo = "x"
EDIT TEXT rec.memo AT 3, 5, 12, 50
IF rec.memo <> "x   y" THEN ERROR 1, "hash field and Tab: [" & rec.memo & "]"
REM A line longer than the box scrolls sideways. Keys: 60 letters, Home, "<", Ctrl-W
EDIT TEXT long$ AT 3, 5, 12, 30
IF long$ <> "<" + REPEAT$("abcdefghij", 6) THEN ERROR 1, "long line: " & long$
COLOR 7, 0
CLS
PRINT "edit_text: all checks passed"
REM EXPECT: edit_text: all checks passed
