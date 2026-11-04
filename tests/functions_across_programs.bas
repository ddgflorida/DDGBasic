REM User-defined FUNCTIONs must work in RUN and CHAIN targets and EVAL strings.
REM Any failed check raises an error (exit 1).
FUNCTION double(x)
  double = x * 2
END FUNCTION

RUN "helpers/fn_child.bas"
IF ERR <> 0 THEN ERROR 1, "RUN child failed: " + ERRMSG$
IF double(6) <> 12 THEN ERROR 1, "caller's function broken after RUN"

REM A function defined by the RUN child must not remain visible here.
leaked = -1
ON ERROR GOTO no_leak
x = triple(2)
GOTO leak_checked
no_leak:
leaked = 0
RESUME leak_checked
leak_checked:
ON ERROR GOTO 0
IF leaked THEN ERROR 1, "RUN child's function leaked into the caller"

result = 0
EVAL "result = double(7)"
IF result <> 14 THEN ERROR 1, "EVAL could not call the caller's function"

CHAIN "helpers/fn_chained.bas"
