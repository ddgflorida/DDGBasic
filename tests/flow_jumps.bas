REM GOSUB/RETURN, ON ERROR/RESUME and GOTO combined with loops and IF blocks. Each part
REM builds a log of what ran and checks it. (Cases found by a bug hunt.)
DIM log AS ARRAY

REM 1. IF ... THEN GOSUB ... ELSE ...: after RETURN the ELSE part is skipped
log$ = ""
x = 1
IF x = 1 THEN GOSUB tag_a ELSE log$ = log$ & "else"
log$ = log$ & "|after"
IF log$ <> "A|after" THEN ERROR 1, "1: " & log$

REM 2. RESUME NEXT into the THEN part of a single-line IF with an ELSE
log$ = ""
ON ERROR GOTO h_log
IF 1 THEN y = 1 / 0 : log$ = log$ & "then-rest" ELSE log$ = log$ & "else"
ON ERROR GOTO 0
IF log$ <> "Hthen-rest" THEN ERROR 1, "2: " & log$

REM 3. An error inside a block IF branch is handled, and the branch goes on
log$ = ""
ON ERROR GOTO h_log
IF 1 THEN
    log$ = log$ & "before|"
    y = 1 / 0
    log$ = log$ & "|after"
END IF
ON ERROR GOTO 0
IF log$ <> "before|H|after" THEN ERROR 1, "3: " & log$

REM 4. RETURN from inside a loop in a subroutine
log$ = ""
FOR i = 1 TO 2
    GOSUB ret_in_loop
    log$ = log$ & "i" & i & " "
NEXT
IF log$ <> "i1 i2 " THEN ERROR 1, "4: " & log$

REM 5. RETURN from inside a block IF in a subroutine called from a WHILE loop
log$ = ""
n = 0
WHILE n < 3
    n = n + 1
    GOSUB ret_in_if
WEND
IF log$ <> "normal1 normal3 " THEN ERROR 1, "5: " & log$

REM 6. A GOTO inside a subroutine stays inside it
log$ = ""
FOR i = 1 TO 3
    GOSUB goto_in_sub
    log$ = log$ & i
NEXT
IF log$ <> "123" THEN ERROR 1, "6: " & log$

REM 7. A GOTO inside an error handler, for an error raised in a loop
log$ = ""
ON ERROR GOTO h_goto
FOR i = 1 TO 3
    IF i = 2 THEN ERROR 5
    log$ = log$ & i
NEXT
ON ERROR GOTO 0
IF log$ <> "1H23" THEN ERROR 1, "7: " & log$

REM 8. RESUME NEXT inside a block IF in the handler
log$ = ""
ON ERROR GOTO h_block
FOR i = 1 TO 3
    IF i = 2 THEN ERROR 5
    log$ = log$ & i
NEXT
ON ERROR GOTO 0
IF log$ <> "1H23" THEN ERROR 1, "8: " & log$

REM 9. RESUME label leaves the loop, once
log$ = ""
ON ERROR GOTO h_label
FOR i = 1 TO 5
    IF i = 3 THEN ERROR 9
    log$ = log$ & i
NEXT
log$ = log$ & "|not reached"
resumed:
ON ERROR GOTO 0
log$ = log$ & "|out" & i
IF log$ <> "12H|out3" THEN ERROR 1, "9: " & log$

REM 10. An error in a block IF's condition: RESUME NEXT goes after END IF
log$ = ""
z = 0
ON ERROR GOTO h_log
IF 10 / z > 1 THEN
    log$ = log$ & "|then"
ELSE
    log$ = log$ & "|else"
END IF
ON ERROR GOTO 0
log$ = log$ & "|after"
IF log$ <> "H|after" THEN ERROR 1, "10: " & log$

REM 11. RETURN inside a FUNCTION does not pop the caller's GOSUB
log$ = ""
ON ERROR GOTO h_msg
GOSUB calls_function
ON ERROR GOTO 0
IF INSTR(log$, "RETURN without GOSUB") = 0 THEN ERROR 1, "11: " & log$

REM 12. GOSUB nested three deep, each returning from inside a loop
depth_log$ = ""
GOSUB level1
IF depth_log$ <> "1(2(3)2)1" THEN ERROR 1, "12: " & depth_log$

PRINT "flow_jumps: all checks passed"
REM EXPECT: flow_jumps: all checks passed
END

tag_a:
    log$ = log$ & "A"
    RETURN
h_log:
    log$ = log$ & "H"
    RESUME NEXT
h_msg:
    log$ = log$ & ERRMSG$
    RESUME NEXT
h_goto:
    GOTO h_goto2
h_goto2:
    log$ = log$ & "H"
    RESUME NEXT
h_block:
    IF ERR = 5 THEN
        log$ = log$ & "H"
        RESUME NEXT
    END IF
    RESUME NEXT
h_label:
    log$ = log$ & "H"
    RESUME resumed
ret_in_loop:
    FOR j = 1 TO 5
        IF j = 2 THEN RETURN
    NEXT
    RETURN
ret_in_if:
    IF n = 2 THEN
        RETURN
    END IF
    log$ = log$ & "normal" & n & " "
    RETURN
goto_in_sub:
    GOTO sub_done
sub_done:
    RETURN
calls_function:
    q = has_return(3)
    RETURN
level1:
    depth_log$ = depth_log$ & "1("
    FOR a = 1 TO 3
        GOSUB level2
        IF a = 1 THEN depth_log$ = depth_log$ & ")1" : RETURN
    NEXT
    RETURN
level2:
    depth_log$ = depth_log$ & "2("
    WHILE 1
        GOSUB level3
        depth_log$ = depth_log$ & ")2"
        RETURN
    WEND
level3:
    DO
        depth_log$ = depth_log$ & "3"
        RETURN
    LOOP

FUNCTION has_return(v)
    has_return = v * 2
    RETURN
END FUNCTION
