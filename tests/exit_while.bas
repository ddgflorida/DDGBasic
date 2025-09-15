REM ===================================================
REM TEST 1: Simple EXIT WHILE in a WHILE...WEND loop
REM ===================================================
PRINT "--- Testing simple WHILE loop ---"
i = 0
WHILE i < 10
    i = i + 1
    PRINT "Looping, i ="; i
    IF i = 4 THEN
        PRINT "Exiting WHILE at i=4"
        EXIT WHILE
    END IF
WEND
PRINT "After simple WHILE loop."
PRINT


REM ==========================================================
REM TEST 2: EXIT WHILE in a nested loop
REM This ensures EXIT WHILE only exits the inner WHILE loop
REM and returns control to the outer FOR loop.
REM ==========================================================
PRINT "--- Testing nested loop with EXIT WHILE ---"
FOR outer_loop = 1 TO 2
    PRINT "Outer loop, iteration:"; outer_loop
    inner_loop = 0
    WHILE inner_loop < 5
        inner_loop = inner_loop + 1
        PRINT "  Inner loop, value ="; inner_loop
        IF inner_loop = 3 THEN
            PRINT "  Exiting inner WHILE loop..."
            EXIT WHILE
        END IF
    WEND
    PRINT "  Returned to outer loop."
NEXT outer_loop
PRINT "After nested loop test."
PRINT

END
