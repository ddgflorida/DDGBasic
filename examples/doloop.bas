REM --- DO...LOOP Examples ---

PRINT "--- 1. DO WHILE (Pre-test) ---"
i = 0
DO WHILE i < 3
	PRINT "i ="; i
	i = i + 1
LOOP
PRINT "Loop finished. Final i ="; i
PRINT

PRINT "--- 2. DO UNTIL (Pre-test) ---"
i = 0
DO UNTIL i >= 3
	PRINT "i ="; i
	i = i + 1
LOOP
PRINT "Loop finished. Final i ="; i
PRINT

PRINT "--- 3. DO...LOOP WHILE (Post-test) ---"
i = 0
DO
	PRINT "i ="; i
	i = i + 1
LOOP WHILE i < 3
PRINT "Loop finished. Final i ="; i
PRINT

PRINT "--- 4. DO...LOOP UNTIL (Post-test) ---"
i = 0
DO
	PRINT "i ="; i
	i = i + 1
LOOP UNTIL i >= 3
PRINT "Loop finished. Final i ="; i
PRINT

PRINT "--- 5. Infinite loop with EXIT DO ---"
i = 0
DO
	PRINT "i ="; i
	i = i + 1
	IF i = 3 THEN
		PRINT "Exiting loop now..."
		EXIT DO
	END IF
LOOP
PRINT "Loop finished. Final i ="; i
PRINT

END