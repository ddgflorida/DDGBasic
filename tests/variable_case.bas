REM Variable names are case-insensitive for reads AND writes; hash keys are not.
REM Any failed check raises an error (exit 1).
Total = 1
total = total + 1
TOTAL = TOTAL + 1
IF Total <> 3 THEN ERROR 1, "Total/total/TOTAL are not one variable: " + STR$(Total)

name$ = "a"
NAME$ = "b"
IF name$ <> "b" THEN ERROR 1, "NAME$ did not update name$"

FUNCTION Square(x)
  square = x * x
END FUNCTION
IF Square(4) <> 16 THEN ERROR 1, "return value assigned in a different case was lost"

DIM arr AS ARRAY
PUSH ARR, 1
PUSH arr, 2
IF UBOUND(Arr) <> 1 THEN ERROR 1, "array statements are case-sensitive"

DIM h AS HASH
h("Key") = 1
h("key") = 2
IF HASH_COUNT(H) <> 2 THEN ERROR 1, "hash keys should stay case-sensitive"

FOR I = 1 TO 3
NEXT i
IF i <> 4 THEN ERROR 1, "FOR I ... NEXT i"
PRINT "variable_case: all checks passed"
