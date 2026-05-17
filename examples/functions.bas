REM ========== UDF TEST ==========

REM --- Test 1: simple numeric function ---
FUNCTION square(x)
  square = x * x
END FUNCTION

PRINT "Test 1: square(7) = "; square(7)
PRINT "Test 1: square(square(3)) = "; square(square(3))

REM --- Test 2: string function with $ suffix ---
FUNCTION greet$(name$)
  greet$ = "Hello, " + name$ + "!"
END FUNCTION

PRINT "Test 2: "; greet$("Dan")

REM --- Test 3: multiple parameters ---
FUNCTION add3(a, b, c)
  add3 = a + b + c
END FUNCTION

PRINT "Test 3: add3(10, 20, 30) = "; add3(10, 20, 30)

REM --- Test 4: param shadowing - outer var must survive ---
x = 999
PRINT "Test 4: x before call = "; x
result = square(5)
PRINT "Test 4: x after call  = "; x; " (must still be 999)"

REM --- Test 5: globals leak (documenting current behavior) ---
total = 0
FUNCTION sum_to(n)
  total = 0
  FOR i = 1 TO n
    total = total + i
  NEXT
  sum_to = total
END FUNCTION

r = sum_to(10)
PRINT "Test 5: sum_to(10) = "; r; "  (correct: 55)"
PRINT "Test 5: total leaked = "; total; "  (will be 55 -- shadow-only-params)"
PRINT "Test 5: i leaked = "; i; "  (will be 11 -- shadow-only-params)"

REM --- Test 6: recursion ---
FUNCTION factorial(n)
  IF n <= 1 THEN
    factorial = 1
  ELSE
    factorial = n * factorial(n - 1)
  END IF
END FUNCTION

PRINT "Test 6: factorial(0) = "; factorial(0)
PRINT "Test 6: factorial(1) = "; factorial(1)
PRINT "Test 6: factorial(5) = "; factorial(5)
PRINT "Test 6: factorial(10) = "; factorial(10)

REM --- Test 7: EXIT FUNCTION ---
FUNCTION abs_safe(x)
  IF x = 0 THEN
    abs_safe = 0
    EXIT FUNCTION
  END IF
  IF x < 0 THEN
    abs_safe = -x
  ELSE
    abs_safe = x
  END IF
END FUNCTION

PRINT "Test 7: abs_safe(0) = "; abs_safe(0)
PRINT "Test 7: abs_safe(-42) = "; abs_safe(-42)
PRINT "Test 7: abs_safe(17) = "; abs_safe(17)

REM --- Test 8: function calling function ---
FUNCTION cube(x)
  cube = x * square(x)
END FUNCTION

PRINT "Test 8: cube(4) = "; cube(4); "  (must be 64)"

REM --- Test 9: function used inside an expression ---
PRINT "Test 9: square(3) + square(4) = "; square(3) + square(4); "  (must be 25)"

REM --- Test 10: function in IF condition ---
IF square(6) > 30 THEN
  PRINT "Test 10: condition true (correct, 36 > 30)"
ELSE
  PRINT "Test 10: BROKEN -- condition should have been true"
END IF

REM --- Test 11: function from a FOR loop ---
PRINT "Test 11: squares 1..5:"
FOR n = 1 TO 5
  PRINT "  "; n; " -> "; square(n)
NEXT

REM --- Test 12: case insensitivity on function name ---
PRINT "Test 12: SQUARE(8) = "; SQUARE(8)
PRINT "Test 12: Square(9) = "; Square(9)

REM --- Test 13: string manipulation function ---
FUNCTION shout$(s$)
  shout$ = UCASE$(s$) + "!!!"
END FUNCTION

PRINT "Test 13: "; shout$("hello world")

REM --- Test 14: zero arguments ---
FUNCTION pi_approx()
  pi_approx = 3.14159
END FUNCTION

PRINT "Test 14: pi_approx() = "; pi_approx()

REM --- Test 15: function reading a global ---
config_factor = 100
FUNCTION scale(x)
  scale = x * config_factor
END FUNCTION

PRINT "Test 15: scale(7) = "; scale(7); "  (must be 700)"

PRINT ""
PRINT "==== ALL UDF TESTS COMPLETE ===="
