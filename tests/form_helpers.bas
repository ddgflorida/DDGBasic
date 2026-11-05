REM GET ... VALID ... MESSAGE, WHEN and LOOKUP, and ALERT(). Keys come from the test
REM runner. Failed checks raise errors.
DATABASE OPEN ":memory:"
CREATE TABLE states (code TEXT, name TEXT); INSERT INTO states VALUES ('CA', 'California'), ('FL', 'Florida'), ('NY', 'New York'), ('TX', 'Texas');
COLOR 15, 1 : CLS
type$ = "P" : state$ = "" : credit = 0 : name$ = ""
@ 3, 5 SAY "Type  : " GET type$ PICTURE "!" VALID type$ = "P" OR type$ = "B" MESSAGE "Type must be P or B"
@ 4, 5 SAY "State : " GET state$ PICTURE "!!" LOOKUP (SELECT code, name FROM states ORDER BY code)
@ 5, 5 SAY "Credit: " GET credit VALID credit <= 5000 MESSAGE "Limit is 5,000" WHEN type$ = "B"
@ 6, 5 SAY "Name  : " GET name$ MESSAGE "Name is required" VALID name$ <> ""
REM Keys: Ctrl-Y "x" Enter (refused, with its message) Ctrl-Y "b" Enter
REM       "zz" Enter (not a state: the list opens) Down Down Enter (NY)
REM       "9999" Enter (refused) Ctrl-Y "4000" Enter / Enter (empty name refused) "Ann" Enter
READ
REM EXPECT: Type must be P or B
REM EXPECT: Limit is 5,000
REM EXPECT: Name is required
IF type$ <> "B" OR state$ <> "NY" OR credit <> 4000 OR name$ <> "Ann" THEN ERROR 1, "first READ: " & type$ & state$ & STR$(credit) & name$

REM WHEN skips the credit field for type P; F2 opens the lookup list
type$ = "P"
@ 3, 5 SAY "Type  : " GET type$ PICTURE "!"
@ 4, 5 SAY "State : " GET state$ PICTURE "!!" LOOKUP (SELECT code, name FROM states ORDER BY code)
@ 5, 5 SAY "Credit: " GET credit WHEN type$ = "B"
@ 6, 5 SAY "Name  : " GET name$
REM Keys: Enter / F2 Down Enter (FL) Enter / Enter (credit is skipped, so this ends READ)
READ
IF state$ <> "FL" THEN ERROR 1, "F2 lookup: " & state$
IF credit <> 4000 THEN ERROR 1, "WHEN should have skipped credit"

REM ALERT: Right Enter -> 2 / Enter -> 1 (the default OK button) / "c" -> 3 / Esc -> 0
a = ALERT("Save changes?;They can't be undone.", "Yes", "No", "Cancel")
b = ALERT("Saved")
c = ALERT("Really?", "Yes", "No", "Cancel")
d = ALERT("Quit?", "Yes", "No")
IF a <> 2 OR b <> 1 OR c <> 3 OR d <> 0 THEN ERROR 1, "ALERT results"
before$ = SAVESCREEN()
REM Keys: Enter
e = ALERT("Restores the screen")
IF SAVESCREEN() <> before$ THEN ERROR 1, "ALERT did not restore the screen"
COLOR 7, 0
CLS
PRINT "form_helpers: all checks passed"
REM EXPECT: form_helpers: all checks passed
