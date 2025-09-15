REM Test NOT operator in various contexts
PRINT "Testing NOT operator..."

x = 10
y = 5
name$ = "Alice"
empty$ = ""
flag = -1

for i = 1 to 5
   print " "
next
REM Test NOT with simple conditions
PRINT "================================ Simple NOT Tests ================================"

IF NOT x > 15 THEN
    PRINT "OK: NOT x > 15 (10 is not > 15)"
ELSE
    PRINT "NOT OK *************************************"
END IF

IF NOT y < 3 THEN
    PRINT "OK: NOT y < 3 (5 is not < 3)" 
ELSE
    PRINT "NOT OK *************************************"
END IF

REM Test NOT with string comparisons
PRINT
PRINT "=== NOT with Strings ==="

IF NOT name$ = "Bob" THEN
    PRINT "OK: NOT name equals Bob"
ELSE
    PRINT "NOT OK *************************************"
END IF

IF NOT empty$ <> "" THEN
    PRINT "OK: NOT empty string not equal to empty"
ELSE
    PRINT "NOT OK *************************************"
END IF

REM Test NOT with boolean variables
PRINT
PRINT "=== NOT with Boolean Variables ==="

IF NOT flag = 0 THEN
    PRINT "OK: NOT flag equals 0 (flag is -1)"
ELSE
    PRINT "NOT OK *************************************"
END IF

IF NOT x = 0 THEN
    PRINT "OK: NOT x equals 0"
ELSE
    PRINT "NOT OK *************************************"
END IF

REM Test NOT with compound conditions
PRINT
PRINT " NOT with AND/OR "

IF NOT (x > 20 AND y > 10) THEN
    PRINT "OK: NOT (false AND false)"
ELSE
    PRINT "NOT OK *************************************"
END IF

IF NOT (x < 5 OR y > 10) THEN
    PRINT "OK: NOT (false OR false)"
ELSE
    PRINT "NOT OK *************************************"
END IF

REM Test double NOT
PRINT "=== Double NOT ==="

IF NOT NOT x > 5 THEN
    PRINT "OK: Double NOT - x > 5"
ELSE
    PRINT "NOT OK *************************************"
END IF

REM Test NOT with parentheses
PRINT
PRINT "=== NOT with Complex Conditions ==="

IF NOT (name$ = "Bob" OR x < 5) THEN
    PRINT "OK: NOT (string false OR numeric false)"
ELSE
    PRINT "NOT OK *************************************"
END IF

IF NOT (empty$ <> "" AND x > 20) THEN
    PRINT "OK: NOT (string false AND numeric false)"
ELSE
    PRINT "NOT OK *************************************"
END IF

REM Test cases that should NOT print
PRINT
PRINT "=== Testing False Cases ==="

IF NOT x > 5 THEN
    PRINT "ERROR: This should not print *********************"
ELSE
    PRINT "OK: NOT x > 5 correctly false"
END IF

IF NOT name$ <> "" THEN
    PRINT "ERROR: This should not print **************************"  
ELSE
    PRINT "OK: NOT non-empty string correctly false"
END IF

PRINT "NOT operator tests complete"
END