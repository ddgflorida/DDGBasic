REM Menu demo: a menu bar with pull-down menus, a pop-up MENU and ALERT message boxes.
REM Keys: arrows, Enter, the first letter of a title or item, or the mouse. Esc on the bar quits.
COLOR 15, 1, 0, 3
GOSUB draw
DO
    choice$ = MENUBAR$("File:New|Open|-|Quit", "View:Colours|Time", "Help:About")
    IF choice$ = "File.New" OR choice$ = "File.Open" THEN x = ALERT(choice$ & " is not part of this demo.")
    IF choice$ = "View.Colours" THEN GOSUB pick_colours
    IF choice$ = "View.Time" THEN x = ALERT("The time is " & TIME$)
    IF choice$ = "Help.About" THEN x = ALERT("Menu demo;MENUBAR$, MENU and ALERT")
LOOP UNTIL choice$ = "File.Quit" OR choice$ = ""
COLOR 7, 0
CLS
PRINT "Bye."
END

draw:
    CLS
    BOX 2, 1, 23, 80, "Menu demo" DOUBLE
    @ 12, 14 SAY "Use the menu bar: arrows and Enter, a letter, or the mouse."
    RETURN

pick_colours:
    pick = MENU(4, 8, "Blue", "Black", "Cyan")
    IF pick = 1 THEN COLOR 15, 1, 0, 3
    IF pick = 2 THEN COLOR 7, 0, 0, 7
    IF pick = 3 THEN COLOR 0, 3, 15, 1
    IF pick > 0 THEN GOSUB draw
    RETURN
REM EXPECT: Bye.
