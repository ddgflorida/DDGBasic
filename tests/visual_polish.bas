REM Menus taller than the screen scroll, pull-downs too; pop-ups with shadows put the screen
REM back exactly; PROGRESS draws and PROGRESS OFF removes its box. Keys come from the test runner.
CLS
FOR i = 1 TO 22
  @ i, 1 SAY REPEAT$("x", 70)
NEXT i
before$ = SAVESCREEN()
DIM items$(29)
FOR i = 1 TO 30
  items$(i - 1) = "Item " & TRIM$(STR$(i))
NEXT i
REM Keys: Down x25 Enter -> item 26 (the menu scrolls); End Enter -> 30; PgDn PgUp Enter -> 1
n = MENU(4, 40, items$)
IF n <> 26 THEN ERROR 1, "scrolled MENU: expected 26, got " & STR$(n)
IF SAVESCREEN() <> before$ THEN ERROR 1, "MENU with a shadow should put the screen back"
n = MENU(4, 40, items$)
IF n <> 30 THEN ERROR 1, "End in a long MENU: expected 30, got " & STR$(n)
n = MENU(4, 40, items$)
IF n <> 1 THEN ERROR 1, "PgDn PgUp in a long MENU: expected 1, got " & STR$(n)
m$ = "Many:"
FOR i = 1 TO 30
  m$ = m$ & "Pick " & TRIM$(STR$(i)) & "|"
NEXT i
REM Keys: Right Enter (open Many) Down x28 Enter -> Pick 29
c$ = MENUBAR$("File:Open|-|Quit", m$ & "Last")
IF c$ <> "Many.Pick 29" THEN ERROR 1, "scrolled pull-down: got " & c$
REM Keys: Enter
a = ALERT("Shadowed", "OK")
before$ = SAVESCREEN(2, 1, 24, 80)
FOR i = 1 TO 200
  PROGRESS i, 200 TITLE "Working"
NEXT i
IF SAVESCREEN(2, 1, 24, 80) = before$ THEN ERROR 1, "PROGRESS should draw a box"
PROGRESS OFF
IF SAVESCREEN(2, 1, 24, 80) <> before$ THEN ERROR 1, "PROGRESS OFF should put the screen back"
PROGRESS OFF
SET SHADOW OFF
BOX 3, 3, 6, 20 SHADOW
SET SHADOW ON
COLOR 7, 0
CLS
PRINT "visual_polish: all checks passed"
REM EXPECT: visual_polish: all checks passed
