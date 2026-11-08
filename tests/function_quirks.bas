REM Function fixes: RIGHT$(s, 0), negative HEX$/OCT$, date formats, FORMATDATE$ masks,
REM numbers as text, VAL prefixes, SOUNDEX, HASH_DELETE result, ARRAY_JOIN default,
REM scientific exponents, and errors for bad arguments. Any failed check raises an error.
IF RIGHT$("hello", 0) <> "" THEN ERROR 1, "RIGHT$(s, 0)"
IF HEX$(-255) <> "-ff" OR OCT$(-8) <> "-10" THEN ERROR 1, "negative HEX$/OCT$"
IF YEAR("07/04/2024") <> 2024 OR DAY("2024/07/04") <> 4 THEN ERROR 1, "date formats"
IF DATEADD("07/04/2024", 1) <> "2024-07-05" THEN ERROR 1, "DATEADD with MM/DD/YYYY"
IF FORMATDATE$("2024-07-04", "Day dd (%a)") <> "Day 04 (Thu)" THEN ERROR 1, "FORMATDATE$ mask: " + FORMATDATE$("2024-07-04", "Day dd (%a)")
IF LEN(10) <> 2 THEN ERROR 1, "LEN(10) = " + STR$(LEN(10))
IF ARRAY_JOIN(ARRAY(1, 2.5, 3), "|") <> "1|2.5|3" THEN ERROR 1, "ARRAY_JOIN numbers"
IF ARRAY_JOIN(ARRAY("a", "b")) <> "a,b" THEN ERROR 1, "ARRAY_JOIN default delimiter"
IF ARRAY_JOIN(FILTER(ARRAY(10, 21, 30), "0"), ",") <> "10,30" THEN ERROR 1, "FILTER matched .0"
IF VAL("12abc") <> 12 OR VAL("abc") <> 0 OR VAL("inf") <> 0 THEN ERROR 1, "VAL prefix"
IF ISNUMERIC("nan") OR ISNUMERIC("inf") THEN ERROR 1, "ISNUMERIC nan/inf"
IF SOUNDEX$("Tymczak") <> "T522" OR SOUNDEX$("Ashcraft") <> "A261" THEN ERROR 1, "SOUNDEX$"
h = PARSEJSON("{""a"": 1}")
IF HASH_DELETE(h, "a") <> -1 OR HASH_DELETE(h, "a") <> 0 THEN ERROR 1, "HASH_DELETE result"
IF FORMAT$(0.000789, "#.##^^^^") <> "7.89E-04" THEN ERROR 1, "negative exponent: " + FORMAT$(0.000789, "#.##^^^^")

bad_args = 0
ON ERROR GOTO caught
x$ = LEFT$("abc")
GOTO after
caught:
IF INSTR(ERRMSG$, "Invalid arguments for LEFT$()") THEN bad_args = 1
RESUME after
after:
ON ERROR GOTO 0
IF bad_args <> 1 THEN ERROR 1, "bad arguments were not reported as a DDGBasic error"
PRINT "function_quirks: all checks passed"
