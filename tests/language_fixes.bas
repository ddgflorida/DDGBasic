REM Language fixes: SORT modifiers in any case, DIM AS INTEGER/STRING, negative index
REM writes, RUN arguments, RECNO from 1 and restored after a nested loop.
REM Failed checks raise errors.
a = ARRAY(3, 1, 2)
sort a desc
IF a(0) <> 3 OR a(2) <> 1 THEN ERROR 1, "sort desc"
DIM n AS INTEGER
DIM s AS STRING
IF TYPENAME$(n) <> "FLOAT" OR TYPENAME$(s) <> "STRING" THEN ERROR 1, "DIM AS INTEGER/STRING"
bad = 0
ON ERROR GOTO neg
b = ARRAY(1, 2, 3)
b(-1) = 9
GOTO after_neg
neg:
bad = 1
RESUME after_neg
after_neg:
ON ERROR GOTO 0
IF bad <> 1 THEN ERROR 1, "negative index write was allowed"

OPEN "recno.csv" FOR OUTPUT AS #1
PRINT #1, "x"
PRINT #1, "1"
PRINT #1, "2"
CLOSE #1
first = 0 : outer$ = ""
FOR r IN CSV "recno.csv" OPTIONS "header=true"
  IF first = 0 THEN first = RECNO
  FOR q IN CSV "recno.csv"
  NEXT
  outer$ = outer$ & STR$(RECNO)
NEXT
IF first <> 1 THEN ERROR 1, "CSV RECNO starts at " + STR$(first)
IF outer$ <> " 1 2" THEN ERROR 1, "outer RECNO after nested loop: " + outer$
KILL "recno.csv"
PRINT "language_fixes: all checks passed"
