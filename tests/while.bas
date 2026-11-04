REM --- Comprehensive WHILE...WEND Loop Test ---

PRINT "--- SECTION 1: Basic Counting Loop ---"
REM Test 1.1: Simple loop counting up from 1 to 5
i = 1
PRINT "Test 1.1: Counting from 1 to 5"
WHILE i <= 5
    PRINT "  i ="; i
    i = i + 1
WEND
PRINT "After loop, i ="; i -- Should be 6
PRINT

REM --- SECTION 2: Edge Cases ---
REM Test 2.1: A loop that should not execute at all
j = 10
PRINT "Test 2.1: Loop while j < 5 (should not run)"
WHILE j < 5
    PRINT "  This should not be printed."
    j = j + 1
WEND
PRINT "After loop, j ="; j -- Should still be 10
PRINT

REM Test 2.2: A loop that executes only once
k = 5
PRINT "Test 2.2: Loop while k = 5"
WHILE k = 5
    PRINT "  k ="; k
    k = k + 1 -- Condition becomes false after this
WEND
PRINT "After loop, k ="; k -- Should be 6
PRINT

REM --- SECTION 3: EXIT WHILE ---
REM Test 3.1: Using EXIT WHILE to leave a loop early
counter = 0
PRINT "Test 3.1: Loop with EXIT WHILE at counter = 3"
WHILE counter < 100
    PRINT "  counter ="; counter
    IF counter = 3 THEN
        PRINT "  Exiting now..."
        EXIT WHILE
    END IF
    counter = counter + 1
WEND
PRINT "After loop, counter ="; counter -- Should be 3
PRINT

REM --- SECTION 4: Nested Loops ---
PRINT "Test 4.1: Nested WHILE loop inside a FOR loop"
FOR outer = 1 TO 2
    PRINT "  Outer loop:"; outer
    inner = 1
    WHILE inner <= 3
        PRINT "    Inner loop:"; inner
        inner = inner + 1
    WEND
NEXT outer
PRINT

PRINT "--- WHILE...WEND test complete. ---"
END