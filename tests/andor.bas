REM Test AND, OR, and NOT operators
PRINT "Testing logical operators..."

x = 10
y = 20
name$ = "John"
empty$ = ""
FOR i = 1 to 5
    PRINT
NEXT
PRINT "====================== AND OR TESTING ================"
REM Basic AND tests
PRINT "=== AND Tests ==="
IF x > 5 AND y > 15 THEN
    PRINT "OK: Both conditions true"
ELSE
    PRINT "NOT OK **********************************"
END IF

IF x > 5 AND y > 25 THEN
    PRINT "NOT OK: Should not print - second condition false ***************"
ELSE
    PRINT "OK: AND correctly failed on false condition"
END IF

REM Basic OR tests  
PRINT "=== OR Tests ==="
IF x > 5 OR y > 25 THEN
    PRINT "OK: OR with first condition true"
ELSE
    PRINT "NOT OK **********************************"
END IF

IF x > 15 OR y > 15 THEN
    PRINT "OK: OR with second condition true" 
END IF

IF x > 15 OR y > 25 THEN
    PRINT "NOT OK: Should not print - both false ************"
ELSE
    PRINT "OK: OR correctly failed on both false"
END IF

REM NOT tests
PRINT "=== NOT Tests ==="
IF NOT x > 15 THEN
    PRINT "OK: NOT works with false condition"
END IF

IF NOT empty$ = "" THEN
    PRINT "NOT OK: Should not print ***************"
ELSE
    PRINT "OK: NOT works with true condition"
END IF

REM Complex combinations
PRINT "=== Complex Tests ==="
IF x > 5 AND (y > 15 OR name$ = "Jane") THEN
    PRINT "OK: AND with OR in parentheses"
END IF
PRINT "Complex:2"
IF (x > 5 OR x < 0) AND y > 15 THEN
    PRINT "OK: OR with AND"
END IF
PRINT "Complex:3"
IF NOT (x > 15 AND y < 10) THEN
    PRINT "OK: NOT with AND in parentheses"
ELSE
    PRINT "NOT OK **********************************"
END IF

PRINT "Complex:4"
REM String and numeric mixed
PRINT "=== Mixed Type Tests ==="
IF name$ <> "" AND x > 0 THEN
    PRINT "OK: String and numeric with AND"
ELSE
    PRINT "NOT OK **********************************"
END IF
PRINT "Complex:5"
IF name$ = "Bob" OR x = 10 THEN
    PRINT "OK: Mixed OR (numeric condition true)"
ELSE
    PRINT "NOT OK **********************************"
END IF

PRINT "Logical operator tests complete"
END