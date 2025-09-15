LET A = 10
B = 20
C = (A * 2) + (B / 2)
PRINT "C should be 30. C is:";
PRINT C

GREETING$ = "HELLO"
WHO$ = "WORLD"
MESSAGE$ = GREETING$ + " " + WHO$
PRINT MESSAGE$

PRINT ""
PRINT "--- TESTING CONDITIONALS ---"

IF C > 25 THEN
	PRINT "C is greater than 25."
END IF

IF C < 25 THEN
	PRINT "This should not print."
ELSE
	PRINT "C is not less than 25. (Correct)"
END IF

IF MESSAGE$ = "HELLO WORLD" THEN
	PRINT "String comparison works!"
END IF

LET X = 5
IF X = 5 THEN
	PRINT "X is 5"
	IF C = 30 THEN
		PRINT "Nested IF works too!"
	END IF
ELSE
	PRINT "This should not appear"
END IF

END
