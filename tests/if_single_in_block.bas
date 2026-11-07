REM A single-line IF ... THEN ... ELSE inside a block IF: its ELSE belongs to the single-line
REM IF, not to the block. (The block once took it as its own ELSE and ran the wrong lines.)
out$ = ""
x = 5
IF x > 100 THEN
    IF x > 1 THEN out$ = out$ & "a" ELSE out$ = out$ & "b"
    out$ = out$ & "c"
END IF
IF out$ <> "" THEN ERROR 1, "false block ran: " & out$
x = 500
IF x > 100 THEN
    IF x > 1000 THEN out$ = out$ & "a" ELSE out$ = out$ & "b"
    out$ = out$ & "c"
ELSE
    out$ = out$ & "d"
END IF
IF out$ <> "bc" THEN ERROR 1, "true block with an ELSE: " & out$
n = 0
FOR i = 1 TO 4
    IF MOD(i, 2) = 0 THEN
        IF n = 0 THEN n = 10 ELSE n = n + 1
    END IF
NEXT i
IF n <> 11 THEN ERROR 1, "in a loop: expected 11, got " & STR$(n)
PRINT "if_single_in_block: all checks passed"
REM EXPECT: if_single_in_block: all checks passed
