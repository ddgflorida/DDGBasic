REM Edge cases in FUNCTION calls

REM 1. Too many nested calls is a BASIC error that ON ERROR can catch
ON ERROR GOTO caught
msg$ = ""
r = depth(500)
ON ERROR GOTO 0
IF INSTR(msg$, "Too many nested function calls") = 0 THEN ERROR 1, "1a: " & msg$
IF depth(30) <> 30 THEN ERROR 1, "1b"

REM 2. DIM in a main-program subroutine reached by GOSUB from a function is global
GOSUB make_list
r = calls_sub(1)
IF ARRAY_SIZE(shared) <> 8 THEN ERROR 1, "2a: " & ARRAY_SIZE(shared)
REM ... while DIM written in the function body is local
own = 5
r = calls_sub(1)
IF own <> 5 THEN ERROR 1, "2b: " & own

REM 3. A function with labels and block IFs, called from EVAL and ${}
EVAL "result = with_label(1) + with_if(5)"
IF result <> 5 THEN ERROR 1, "3a: " & result
IF `${with_label(2)}` <> "6" THEN ERROR 1, "3b"

REM 4. A parameter cannot take the function's name (the name holds the result)
ON ERROR GOTO caught
msg$ = ""
EVAL "FUNCTION twice(twice)" & CHR$(10) & "twice = 2" & CHR$(10) & "END FUNCTION"
ON ERROR GOTO 0
IF INSTR(msg$, "cannot have the function's name") = 0 THEN ERROR 1, "4: " & msg$

PRINT "function_edges: all checks passed"
REM EXPECT: function_edges: all checks passed
END

caught:
    msg$ = ERRMSG$
    RESUME NEXT

make_list:
    DIM shared(3)
    RETURN

grow_list:
    DIM shared(7)
    RETURN

FUNCTION depth(n)
    IF n = 0 THEN
        depth = 0
    ELSE
        depth = 1 + depth(n - 1)
    END IF
END FUNCTION

FUNCTION calls_sub(x)
    GOSUB grow_list
    DIM own(2)
    calls_sub = x
END FUNCTION

FUNCTION with_label(x)
    GOSUB bump
    with_label = x * 2
    EXIT FUNCTION
bump:
    x = x + 1
    RETURN
END FUNCTION

FUNCTION with_if(x)
    IF x > 1 THEN
        with_if = 1
    ELSE
        with_if = 2
    END IF
END FUNCTION
