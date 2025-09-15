REM ===============================================
REM TEST 1: EXIT FOR with FOR...TO...NEXT loop
REM ===============================================
PRINT "--- Testing FOR...NEXT ---"
FOR i = 1 TO 10
    PRINT "Looping, i ="; i
    IF i = 3 THEN
        PRINT "Exiting FOR...NEXT at i=3"
        EXIT FOR
    END IF
NEXT i
PRINT "After FOR...NEXT loop."
PRINT


REM ===============================================
REM TEST 2: EXIT FOR with FOR EACH...IN HASH loop
REM ===============================================
PRINT "--- Testing FOR EACH IN HASH ---"
DIM h AS HASH
h("alpha") = 1
h("beta") = 2
h("gamma") = 3

FOR EACH key$ IN HASH h
    PRINT "Looping, key$ = "; key$
    IF key$ = "beta" THEN
        PRINT "Exiting FOR EACH at key$='beta'"
        EXIT FOR
    END IF
NEXT
PRINT "After FOR EACH loop."
PRINT


REM ===============================================
REM TEST 3: EXIT FOR with FOR...IN (SQL) loop
REM ===============================================
PRINT "--- Testing FOR...IN (SQL) ---"
DATABASE OPEN ":memory:"
CREATE TABLE users (id INTEGER, name TEXT);
INSERT INTO users VALUES (10, 'Alice'), (20, 'Bob'), (30, 'Charlie');

FOR row IN (SELECT id, name FROM users ORDER BY id)
    PRINT "Looping, id ="; row.id; ", name = "; row.name
    IF row.id = 20 THEN
        PRINT "Exiting SQL loop at id="; row.id; " via EXIT FOR"
        EXIT FOR
    END IF
NEXT
PRINT "After SQL loop."
DATABASE CLOSE
PRINT


REM ===============================================
REM TEST 4: EXIT FOR with FOR...IN CSV loop
REM ===============================================
PRINT "--- Testing FOR...IN CSV ---"
REM Create a temporary CSV file to test with
OPEN "exit_test.csv" FOR OUTPUT AS #1
PRINT #1, "100,apple"
PRINT #1, "200,banana"
PRINT #1, "300,cherry"
CLOSE #1

REM Now, read the file and test the loop exit
FOR rec IN CSV ("exit_test.csv")
    PRINT "Looping, value ="; rec(1)
    IF rec(1) = 200 THEN
        PRINT "Exiting CSV loop at value=200"
        EXIT FOR
    END IF
NEXT
PRINT "After CSV loop."
KILL "exit_test.csv"
PRINT

END