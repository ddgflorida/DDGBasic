REM --- Comprehensive FOR...NEXT Loop Test ---
PRINT "--- SECTION 1: Basic Loops ---"
REM Test 1.1: Simple loop counting up from 1 to 5
PRINT "Test 1.1: Counting from 1 to 5"
FOR i = 1 TO 5
    PRINT "  i ="; i
NEXT i
PRINT "After loop, i ="; i -- Should be 6
PRINT

REM Test 1.2: Loop with a STEP of 2
PRINT "Test 1.2: Counting from 1 to 10 with STEP 2"
FOR j = 1 TO 10 STEP 2
    PRINT "  j ="; j
NEXT j
PRINT "After loop, j ="; j -- Should be 11
PRINT

REM --- SECTION 2: Loops Counting Down ---
REM Test 2.1: Simple loop counting down from 5 to 1
PRINT "Test 2.1: Counting down from 5 to 1"
FOR k = 5 TO 1 STEP -1
    PRINT "  k ="; k
NEXT k
PRINT "After loop, k ="; k -- Should be 0
PRINT

REM Test 2.2: Loop counting down with a larger negative step
PRINT "Test 2.2: Counting down from 10 to 0 with STEP -3"
FOR l = 10 TO 0 STEP -3
    PRINT "  l ="; l
NEXT l
PRINT "After loop, l ="; l -- Should be -2
PRINT

REM --- SECTION 3: Edge Cases ---
REM Test 3.1: A loop that should not execute at all
PRINT "Test 3.1: Loop from 10 to 1 (should not run)"
FOR m = 10 TO 1
    PRINT "  This should not be printed."
NEXT m
PRINT "After loop, m ="; m -- Should be 10 (its initial value)
PRINT

REM Test 3.2: A loop that executes only once
PRINT "Test 3.2: Loop from 5 to 5"
FOR n = 5 TO 5
    PRINT "  n ="; n
NEXT n
PRINT "After loop, n ="; n -- Should be 6
PRINT

REM --- SECTION 4: Nested Loops ---
PRINT "Test 4.1: Nested loops (3x2)"
FOR outer = 1 TO 3
    PRINT "  Outer loop:"; outer
    FOR inner = 1 TO 2
        PRINT "    Inner loop:"; inner
    NEXT inner
NEXT outer
PRINT

PRINT "--- FOR...NEXT test complete. ---"
END
