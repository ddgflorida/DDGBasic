PRINT "Testing DO...LOOP structures"
PRINT "=============================="
PRINT ""

PRINT "Test 1: DO WHILE (pre-test, continue while true)"
x = 1
DO WHILE x <= 5
    PRINT "  x = "; x
    x = x + 1
LOOP

PRINT ""
PRINT "Test 2: DO UNTIL (pre-test, continue until true)"
x = 1
DO UNTIL x > 5
    PRINT "  x = "; x
    x = x + 1
LOOP

PRINT ""
PRINT "Test 3: DO...LOOP WHILE (post-test, at least once)"
x = 10
DO
    PRINT "  x = "; x; " (executes at least once)"
    x = x + 1
LOOP WHILE x <= 5

PRINT ""
PRINT "Test 4: DO...LOOP UNTIL (post-test)"
x = 1
DO
    PRINT "  x = "; x
    x = x + 1
LOOP UNTIL x > 5

PRINT ""
PRINT "Test 5: DO...LOOP with EXIT LOOP"
x = 1
DO
    PRINT "  x = "; x
    x = x + 1
    IF x > 3 THEN EXIT LOOP
LOOP

PRINT ""
PRINT "Test 6: Nested DO loops"
y = 0
DO WHILE y < 3
    y = y + 1
    x = 0
    DO
        x = x + 1
        PRINT "  y="; y; " x="; x
    LOOP UNTIL x >= 2
LOOP
END
