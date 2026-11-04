REM SHIFT removes the first element (index 0) and UNSHIFT inserts at index 0.
REM Any failed check raises an error (exit 1).
a = ARRAY("apple", "banana", "cherry")
SHIFT a INTO first$
IF first$ <> "apple" THEN ERROR 1, "SHIFT returned " + first$
IF a(0) <> "banana" THEN ERROR 1, "after SHIFT a(0) is " + a(0)
UNSHIFT a, "kiwi"
IF a(0) <> "kiwi" THEN ERROR 1, "after UNSHIFT a(0) is " + a(0)
IF UBOUND(a) <> 2 THEN ERROR 1, "UBOUND after SHIFT + UNSHIFT"

REM A queue built with PUSH drains completely, including a one-element array.
DIM q AS ARRAY
PUSH q, "job1"
PUSH q, "job2"
PUSH q, "job3"
done$ = ""
WHILE UBOUND(q) >= 0
  SHIFT q INTO job$
  done$ = done$ + job$ + " "
WEND
IF done$ <> "job1 job2 job3 " THEN ERROR 1, "queue order: " + done$

REM SHIFT on an empty array is an error.
ON ERROR GOTO empty_ok
SHIFT q
ERROR 1, "SHIFT on an empty array did not raise an error"
empty_ok:
PRINT "shift_unshift: all checks passed"
END
