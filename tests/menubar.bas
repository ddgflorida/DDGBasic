REM MENUBAR$: a menu bar with pull-down menus. Keys come from the test runner.
REM Failed checks raise errors.
COLOR 15, 1 : CLS
@ 10, 10 SAY "Main screen text"
before$ = SAVESCREEN(2, 1, 24, 80)
got$ = ""
DO
    c$ = MENUBAR$("File:Open|Save|-|Quit", "Customers:Browse|Add|Report", "Help:About", "Exit")
    IF SAVESCREEN(2, 1, 24, 80) <> before$ THEN ERROR 1, "the pull-down was not removed"
    got$ = got$ + "[" + c$ + "]"
LOOP UNTIL c$ = "File.Quit" OR c$ = ""
REM Keys: Enter Down Enter / Right Enter Down Down Enter / Enter Right Right Enter (Help.About)
REM       "c" "a" (hot keys) / Enter Up Enter (Up skips the separator to Quit)
IF got$ <> "[File.Save][Customers.Report][Help.About][Customers.Add][File.Quit]" THEN ERROR 1, "choices: " & got$
REM Keys: Right Enter (a title with no items) / Enter Esc Esc (Esc closes the pull-down, then the bar)
IF MENUBAR$("File:Open", "Exit") <> "Exit" THEN ERROR 1, "title without items"
IF MENUBAR$("File:Open", "Exit") <> "" THEN ERROR 1, "Esc should return an empty string"
REM An array of menus, and a bar on another row. Keys: Enter Enter
menus = SPLIT("Tools:Sort;Reports:Daily", ";")
IF MENUBAR$(3, menus) <> "Tools.Sort" THEN ERROR 1, "array of menus on row 3"
COLOR 7, 0
CLS
PRINT "menubar: all checks passed"
REM EXPECT: menubar: all checks passed
