REM Edge cases in expressions and formatting

REM 1. FORMAT$: scientific notation rounds into the next power, zero-fill
REM    positions show their commas, and 9 counts as a digit after the point
IF FORMAT$(9.99, "#.#^^^^") <> "1.0E+01" THEN ERROR 1, "1a: " & FORMAT$(9.99, "#.#^^^^")
IF FORMAT$(1234, "0,000,000") <> "0,001,234" THEN ERROR 1, "1b: " & FORMAT$(1234, "0,000,000")
IF FORMAT$(1.5, "#.9") <> "1.5" THEN ERROR 1, "1c: " & FORMAT$(1.5, "#.9")

REM 2. String functions take numbers as PRINT shows them (5, not 5.0)
s$ = RIGHT$(12345, 2) & UCASE$(5) & TRIM$(7) & REVERSE$(123) & REPEAT$(1, 3) & REPLACE$(1212, 1, 3)
IF s$ <> "45573211113232" THEN ERROR 1, "2a: " & s$
IF NOT CONTAINS(123, 2) THEN ERROR 1, "2b"

REM 3. Arithmetic errors are BASIC errors
ON ERROR GOTO caught
msg$ = "" : x = (-8) ^ (1 / 3)
IF INSTR(msg$, "fractional power") = 0 THEN ERROR 1, "3a: " & msg$
msg$ = "" : x = 10 ^ 400
IF msg$ <> "Overflow" THEN ERROR 1, "3b: " & msg$
msg$ = "" : x = 1E308 * 10
IF msg$ <> "Overflow" THEN ERROR 1, "3c: " & msg$
msg$ = "" : x = MOD(5, 0)
IF msg$ <> "Division by zero" THEN ERROR 1, "3d: " & msg$
msg$ = "" : x = -"abc"
IF INSTR(msg$, "Type mismatch") = 0 THEN ERROR 1, "3e: " & msg$
ON ERROR GOTO 0
IF MOD("7", 3) <> 1 THEN ERROR 1, "3f"

REM 4. + adds only text that reads as a number; "nan", "inf" and "1_000" are joined
IF "nan" + 1 <> "nan1" OR "inf" + 1 <> "inf1" OR "1_000" + 1 <> "1_0001" THEN ERROR 1, "4a"
IF "12.5" + 1 <> 13.5 THEN ERROR 1, "4b"

REM 5. Numbers past 16 digits print in exponent form, not as float noise
IF TRIM$(STR$(12345678901234567890)) <> "1.2345678901234567e+19" THEN ERROR 1, "5: " & STR$(12345678901234567890)

REM 6. PRINT USING: NULL is an empty field, ; separates values, numbers fit text fields
DATABASE OPEN ":memory:"
n = (SELECT NULL)
OPEN "pu.txt" FOR OUTPUT AS #1
FOR r IN (SELECT NULL AS n, 5 AS f)
    PRINT #1, USING "[###] [&]"; r.n; r.f
NEXT
CLOSE #1
OPEN "pu.txt" FOR INPUT AS #1
LINE INPUT #1, line$
CLOSE #1
IF line$ <> "[   ] [5]" THEN ERROR 1, "6: " & line$

REM 7. Conditions inside ${}
x = 5
IF `${x > 3}` <> "-1" THEN ERROR 1, "7"

PRINT "expression_edges: all checks passed"
REM EXPECT: expression_edges: all checks passed
END

caught:
    msg$ = ERRMSG$
    RESUME NEXT
