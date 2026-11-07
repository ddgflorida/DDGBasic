REM Edge cases in arrays and hashes

REM 1. SORT of an empty array still reads its ON / WITH / DESC clauses
e = ARRAY()
SORT e ON "name" DESC
SORT e WITH neg DESC
IF ARRAY_SIZE(e) <> 0 THEN ERROR 1, "1"

REM 2. SORT WITH sorts in place, so every name for the array sees the order
a = ARRAY(1, 3, 2)
b = a
SORT a WITH neg
IF ARRAY_JOIN(b, ",") <> "3,2,1" THEN ERROR 1, "2: " & ARRAY_JOIN(b, ",")

REM 3. HASH_JOIN makes a new hash: changing it leaves the originals alone
h1 = PARSEJSON("{""id"": 1, ""t"": {""x"": 1}}")
h2 = PARSEJSON("{""v"": 2}")
j = HASH_JOIN(h1, h2)
j.t.x = 99
IF h1.t.x <> 1 OR j.v <> 2 THEN ERROR 1, "3"

REM 4. JSON keeps accented text as it is
IF JSON_SERIALIZE$(ARRAY("café")) <> "[""café""]" THEN ERROR 1, "4: " & JSON_SERIALIZE$(ARRAY("café"))

REM 5. A text array index is a BASIC error, and a number in text is a number
ON ERROR GOTO caught
msg$ = "" : x = a("abc")
IF INSTR(msg$, "Array index must be a number") = 0 THEN ERROR 1, "5a: " & msg$
ON ERROR GOTO 0
IF a("1") <> 2 THEN ERROR 1, "5b"

PRINT "collection_edges: all checks passed"
REM EXPECT: collection_edges: all checks passed
END

caught:
    msg$ = ERRMSG$
    RESUME NEXT

FUNCTION neg(x)
    neg = -x
END FUNCTION
