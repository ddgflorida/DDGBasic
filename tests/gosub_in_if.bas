REM GOSUB inside a block IF (THEN, ELSEIF, ELSE), inside loops, and from a subroutine
REM that has its own block IF. Each subroutine runs and RETURN comes back into the branch.
n = 0
FOR i = 1 TO 3
    IF i = 2 THEN
        GOSUB add
    ELSE
        GOSUB twice
    END IF
NEXT i
IF n <> 5 THEN ERROR 1, "GOSUB in IF/ELSE inside a FOR: expected 5, got " & STR$(n)
IF n > 0 THEN
    FOR j = 1 TO 2
        GOSUB add
    NEXT j
END IF
IF n <> 7 THEN ERROR 1, "GOSUB in a FOR inside an IF: expected 7, got " & STR$(n)
k$ = "INS"
IF k$ = "F4" THEN
    n = 0
ELSEIF k$ = "INS" THEN
    GOSUB add
    n = n * 10
END IF
IF n <> 80 THEN ERROR 1, "GOSUB in ELSEIF, then the rest of the branch: expected 80, got " & STR$(n)
PRINT "gosub_in_if: all checks passed"
REM EXPECT: gosub_in_if: all checks passed
END
twice:
    IF n >= 0 THEN
        GOSUB add
        GOSUB add
    END IF
    RETURN
add:
    n = n + 1
    RETURN
