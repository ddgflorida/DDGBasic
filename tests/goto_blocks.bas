REM GOTO out of a loop or block IF ends that block; GOTO within a block continues it.
REM Any failed check raises an error (exit 1).
REM 1. GOTO out of a FOR loop
FOR i = 1 TO 10
  IF i = 3 THEN GOTO found
NEXT
ERROR 1, "GOTO out of FOR did not jump"
found:
IF i <> 3 THEN ERROR 1, "FOR variable after GOTO = " + STR$(i)

REM 2. GOTO out of a block IF goes to the label, not to END IF
reached_after_if = 0
IF 1 THEN
  GOTO past_if
END IF
reached_after_if = 1
past_if:
IF reached_after_if THEN ERROR 1, "GOTO out of a block IF landed after END IF"

REM 3. GOTO inside a loop body (skip an iteration)
total = 0
FOR i = 1 TO 5
  IF i = 3 THEN GOTO skip
  total = total + i
skip:
NEXT
IF total <> 12 THEN ERROR 1, "GOTO inside a loop body, total = " + STR$(total)

REM 4. out of nested loops
n = 0
DO
  WHILE n < 100
    FOR k = 1 TO 10
      n = n + 1
      IF n = 25 THEN GOTO out_nested
    NEXT
  WEND
LOOP
out_nested:
IF n <> 25 THEN ERROR 1, "nested loops, n = " + STR$(n)

REM 5. jumping out of a loop many times must not build up nesting
rounds = 0
again:
rounds = rounds + 1
FOR j = 1 TO 10
  IF j = 2 THEN GOTO next_round
NEXT
next_round:
IF rounds < 3000 THEN GOTO again

REM 6. GOTO inside a FUNCTION body
FUNCTION sign(a)
  IF a > 0 THEN GOTO positive
  sign = -1
  EXIT FUNCTION
positive:
  sign = 1
END FUNCTION
IF sign(5) <> 1 OR sign(-5) <> -1 THEN ERROR 1, "GOTO inside a FUNCTION"
PRINT "goto_blocks: all checks passed"
