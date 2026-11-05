REM Comparisons in assignments, PRINT and function arguments; .5 and 1e3 literals;
REM SQL NULL in expressions acts as "". Any failed check raises an error (exit 1).
a = 5 : b = 3
x = a > b
IF x <> -1 THEN ERROR 1, "x = a > b gave " + STR$(x)
y = a = b
IF y <> 0 THEN ERROR 1, "y = a = b gave " + STR$(y)
ok = a > 1 AND b < 10
IF ok <> -1 THEN ERROR 1, "AND in an assignment"
IF ABS(a > b) <> 1 THEN ERROR 1, "comparison as a function argument"
s$ = "abc"
IF s$ <> "abc" THEN ERROR 1, "plain string assignment changed"

IF .5 <> 0.5 THEN ERROR 1, ".5 literal"
IF 1e3 <> 1000 THEN ERROR 1, "1e3 literal"
IF 2.5E-2 <> 0.025 THEN ERROR 1, "2.5E-2 literal"
h = PARSEJSON("{""k"": 7}")
IF h.k <> 7 THEN ERROR 1, "hash dot access broken"

DATABASE OPEN ":memory:"
t$ = "[" + (SELECT NULL) + "]"
IF t$ <> "[]" THEN ERROR 1, "NULL in an expression gave " + t$
IF LEN((SELECT NULL)) <> 0 THEN ERROR 1, "LEN of NULL"
n = (SELECT NULL)
IF n <> 0 THEN ERROR 1, "NULL assigned to a numeric variable should be 0"
PRINT "expressions: all checks passed"
