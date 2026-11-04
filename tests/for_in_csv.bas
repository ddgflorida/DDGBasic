REM --- Comprehensive FOR...IN CSV with NEXT Test ---

REM --- 1. Create a temporary CSV file ---
PRINT "--- 1. Creating temporary file: test_data.csv ---"
OPEN "test_data.csv" FOR OUTPUT AS #1
PRINT #1, "ID,Name,Status"
PRINT #1, "101,Widget,ACTIVE"
PRINT #1, "102,Gadget,INACTIVE"
CLOSE #1
PRINT "-> File created."
PRINT

REM --- 2. Test with header=false (default) ---
PRINT "--- 2. Testing headerless iteration (access by index) ---"
TRON
FOR rec IN CSV ("test_data.csv")
    REM Skip the header row manually
	REM IF rec(1) <> "ID" THEN
	   PRINT "Record:", rec(1); ", "; rec(2); ", "; rec(3)
	REM END IF
NEXT
TROFF
PRINT "-> Headerless test complete."
PRINT

REM --- 3. Test with header=true and nested loop ---
PRINT "--- 3. Testing header iteration with a nested loop ---"
FOR rec IN CSV ("test_data.csv") OPTIONS "header=true"
PRINT "---"
PRINT "  Outer Loop Record -> ID:", rec.id, "Name:", rec.name$

REM This nested loop is the critical test
FOR i = 1 TO 2
    PRINT "    Inner loop iteration:"; i
NEXT i

PRINT "  Resumed outer loop."

NEXT

PRINT "-> Header and nested loop test complete."
PRINT

REM --- 4. Cleanup ---
PRINT "--- 4. Cleaning up ---"
KILL "test_data.csv"