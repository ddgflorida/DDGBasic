REM Small fixes: single-line IF with several statements in each branch, FOR ... IN CSV
REM options, ANALYZE CSV DATE suggestions, and FETCH setting ERRMSG$. Failed checks raise errors.
c = 1 : a = 0 : b = 0 : d = 0 : e = 0
IF c THEN a = 1 : b = 2 ELSE d = 3 : e = 4
IF a <> 1 OR b <> 2 OR d <> 0 OR e <> 0 THEN ERROR 1, "THEN part with two statements"
c = 0
IF c THEN a = 9 : b = 9 ELSE d = 5 : e = 6
IF a <> 1 OR d <> 5 OR e <> 6 THEN ERROR 1, "ELSE part with two statements"
x = 1 : y = 0 : r$ = ""
IF x THEN IF y THEN r$ = "both" ELSE r$ = "x only"
IF r$ <> "x only" THEN ERROR 1, "nested IF ... ELSE: " & r$
s$ = ""
FOR i = 1 TO 3: IF i = 2 THEN s$ = s$ & "two" ELSE s$ = s$ & STR$(i) : NEXT
IF s$ <> " 1two 3" THEN ERROR 1, "NEXT after ELSE: [" & s$ & "]"
k = 0 : w$ = ""
WHILE k < 3: k = k + 1: IF k = 2 THEN w$ = w$ & "w" ELSE w$ = w$ & "k" : WEND
IF w$ <> "kwk" THEN ERROR 1, "WEND after ELSE: " & w$
n = 0
IF c THEN FOR j = 1 TO 2: n = n + 1: NEXT ELSE n = 100
IF n <> 100 THEN ERROR 1, "an inline FOR in a skipped THEN part"

got$ = ""
FOR rec IN CSV "data/semi.csv" OPTIONS "header=true, delimiter=;, skip=1"
    got$ = got$ & rec.name & "=" & rec.qty & "@" & rec("Unit Price") & " "
NEXT
IF got$ <> "A=1@2.50 B=2@1.25 " THEN ERROR 1, "FOR IN CSV options: " & got$
n = 0
FOR rec IN CSV "data/semi.csv" OPTIONS "header=true, delimiter=auto, skip=1"
    n = n + 1
NEXT
IF n <> 2 THEN ERROR 1, "delimiter=auto and blank lines: " & STR$(n)

ANALYZE CSV "data/dates.csv" INTO rep
cs = rep("COLUMN_STATISTICS")
st = cs("joined")
IF st("SUGGESTED_DATA_TYPE") <> "DATE" THEN ERROR 1, "dates should suggest DATE"
st = cs("mixed")
IF st("SUGGESTED_DATA_TYPE") <> "TEXT" THEN ERROR 1, "dates mixed with numbers should suggest TEXT"

FETCH "http://127.0.0.1:1/nothing" INTO page$
IF ERR <> -1 OR ERRMSG$ = "" THEN ERROR 1, "FETCH network error should set ERR = -1 and ERRMSG$"
PRINT "small_fixes: all checks passed"
REM EXPECT: small_fixes: all checks passed
