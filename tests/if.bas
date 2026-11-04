REM --- Comprehensive IF Statement Test ---
PRINT "--- Initializing Test Variables ---"
x = 10
y = 20
z$ = "hello"
PRINT "x=10, y=20, z$=""hello"""
PRINT

REM ===============================================
PRINT "--- SECTION 1: Single-Line IF Statements ---"
REM ===============================================
REM Test 1.1: Simple true condition
IF x = 10 THEN PRINT "Test 1.1 Passed: Simple true condition."

REM Test 1.2: Simple false condition (should do nothing)
IF x = 99 THEN PRINT "Test 1.2 Failed: False condition was executed."

REM Test 1.3: Multi-statement on one line (using colon)
IF z$ = "hello" THEN PRINT "Test 1.3 Passed: Multi-statement THEN." : PRINT "           (Second part executed)"

REM Test 1.4: String comparison
IF "APPLE" < "BANANA" THEN PRINT "Test 1.4 Passed: String comparison."
PRINT

REM ===============================================
PRINT "--- SECTION 2: Block IF...END IF (No ELSE) ---"
REM ===============================================
REM Test 2.1: Block with a true condition
IF y > x THEN
    PRINT "Test 2.1 Passed: Block IF with true condition."
END IF

REM Test 2.2: Block with a false condition (should skip)
IF y < x THEN
    PRINT "Test 2.2 Failed: False block was executed."
END IF
PRINT

REM ===============================================
PRINT "--- SECTION 3: Block IF...ELSE...END IF ---"
REM ===============================================
REM Test 3.1: True condition, should run THEN block
IF x <= 10 THEN
    PRINT "Test 3.1 Passed: Executed THEN block correctly."
ELSE
    PRINT "Test 3.1 Failed: Executed ELSE block instead of THEN."
END IF

REM Test 3.2: False condition, should run ELSE block
IF x > 10 THEN
    PRINT "Test 3.2 Failed: Executed THEN block instead of ELSE."
ELSE
    PRINT "Test 3.2 Passed: Executed ELSE block correctly."
END IF

REM Test 3.3: Using the NOT operator
a = 0 -- In BASIC, 0 is false
IF NOT a THEN
    PRINT "Test 3.3 Passed: NOT operator with false (0) value."
ELSE
    PRINT "Test 3.3 Failed: NOT operator."
END IF
PRINT

REM ===============================================
PRINT "--- SECTION 4: Nested IF Statements ---"
REM ===============================================
IF x = 10 THEN
    PRINT "Test 4.1: Outer condition passed."
    IF y = 20 THEN
        PRINT "Test 4.1 Passed: Inner condition passed."
    ELSE
        PRINT "Test 4.1 Failed: Inner ELSE block executed."
    END IF
ELSE
    PRINT "Test 4.1 Failed: Outer ELSE block executed."
END IF
PRINT

REM ===============================================
PRINT "--- SECTION 5: Complex Conditions ---"
REM ===============================================
REM Test 5.1: Mathematical expression in condition
IF (y - x) * 2 = 20 THEN
    PRINT "Test 5.1 Passed: Complex math in condition."
END IF

REM Test 5.2: Function call in condition
IF LEN(z$) = 5 THEN
    PRINT "Test 5.2 Passed: Function call in condition."
END IF
PRINT

PRINT "--- IF statement test complete. ---"
END
