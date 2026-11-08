REM --- DDGBasic Hash Key Case Sensitivity Test ---
REM Test both PRESERVE_CASE and IGNORE_CASE modes

PRINT "=== TESTING PRESERVE_CASE MODE (Default) ==="
PRINT

REM Test 1: Basic dot notation assignment and access
DIM person AS HASH
person.firstName = "Alice"
person.lastName = "Smith"
person.age = 30

PRINT "Stored hash:"
PRINT person
PRINT

PRINT "Dot notation access tests (should all PASS - dot notation is forgiving):"
result$ = person.firstName
IF result$ = "Alice" THEN PRINT "PASS: person.firstName" ELSE PRINT "FAIL: person.firstName"

result$ = person.FIRSTNAME  
IF result$ = "Alice" THEN PRINT "PASS: person.FIRSTNAME" ELSE PRINT "FAIL: person.FIRSTNAME"

result$ = person.firstname
IF result$ = "Alice" THEN PRINT "PASS: person.firstname" ELSE PRINT "FAIL: person.firstname"

result$ = person.FirstName
IF result$ = "Alice" THEN PRINT "PASS: person.FirstName" ELSE PRINT "FAIL: person.FirstName"
PRINT

REM Test 2: Bracket notation (should be case-sensitive in PRESERVE_CASE)
PRINT "Bracket notation access tests:"
result$ = person("firstName")
IF result$ = "Alice" THEN PRINT "PASS: person(""firstName"")" ELSE PRINT "FAIL: person(""firstName"")"

result$ = person("FIRSTNAME$")
IF result$ = "" THEN PRINT "PASS: person(""FIRSTNAME"") should fail" ELSE PRINT "FAIL: person(""FIRSTNAME"") should be empty:"; result$

result$ = person("firstname$") 
IF result$ = "" THEN PRINT "PASS: person(""firstname"") should fail" ELSE PRINT "FAIL: person(""firstname"") should be empty:"; result$
PRINT

REM Test 3: HASH_EXISTS function
PRINT "HASH_EXISTS tests in PRESERVE_CASE mode:"
result = HASH_EXISTS(person(), "firstName")
IF result = -1 THEN PRINT "PASS: HASH_EXISTS exact case" ELSE PRINT "FAIL: HASH_EXISTS exact case"

result = HASH_EXISTS(person(), "FIRSTNAME")
IF result = 0 THEN PRINT "PASS: HASH_EXISTS wrong case should fail" ELSE PRINT "FAIL: HASH_EXISTS wrong case"

result = HASH_EXISTS(person(), "missing")
IF result = 0 THEN PRINT "PASS: HASH_EXISTS missing key" ELSE PRINT "FAIL: HASH_EXISTS missing key"
PRINT

REM Test 4: Mixed case assignment via bracket notation
person("mixedCase") = "test1"
person("MIXEDCASE") = "test2"
PRINT "After mixed case bracket assignments:"
PRINT person
PRINT "Should have both 'mixedCase' and 'MIXEDCASE' as separate keys:"
exists1 = HASH_EXISTS(person(), "mixedCase")
exists2 = HASH_EXISTS(person(), "MIXEDCASE")
IF exists1 = -1 AND exists2 = -1 THEN PRINT "PASS: Separate keys created" ELSE PRINT "FAIL: Keys should be separate"
PRINT

PRINT "========================================"
PRINT "=== SWITCHING TO IGNORE_CASE MODE ==="
PRINT "========================================"

SET HASH_KEYS IGNORE_CASE

REM Test 5: New hash in IGNORE_CASE mode
DIM product AS HASH
product.itemName = "Widget"
product.itemCode = "W123" 
product.price = 29.99

PRINT "Hash created in IGNORE_CASE mode:"
PRINT product
PRINT

PRINT "Dot notation access (should all PASS):"
result$ = product.itemName
IF result$ = "Widget" THEN PRINT "PASS: product.itemName" ELSE PRINT "FAIL: product.itemName"

result$ = product.ITEMNAME
IF result$ = "Widget" THEN PRINT "PASS: product.ITEMNAME" ELSE PRINT "FAIL: product.ITEMNAME"

result$ = product.itemname
IF result$ = "Widget" THEN PRINT "PASS: product.itemname" ELSE PRINT "FAIL: product.itemname"
PRINT

PRINT "Bracket notation (should all PASS in IGNORE_CASE):"
result$ = product("itemName")
IF result$ = "Widget" THEN PRINT "PASS: product(""itemName"")" ELSE PRINT "FAIL: product(""itemName"")"

result$ = product("ITEMNAME")
IF result$ = "Widget" THEN PRINT "PASS: product(""ITEMNAME"")" ELSE PRINT "FAIL: product(""ITEMNAME"")"

result$ = product("itemname")
IF result$ = "Widget" THEN PRINT "PASS: product(""itemname"")" ELSE PRINT "FAIL: product(""itemname"")"
PRINT

REM Test 6: Key overwriting test in IGNORE_CASE mode
original_count = HASH_COUNT(product())
product("ItemName") = "Updated Widget"
new_count = HASH_COUNT(product())
IF new_count = original_count THEN PRINT "PASS: Key overwritten, not duplicated" ELSE PRINT "FAIL: Key was duplicated instead of overwritten"

PRINT "Hash after case variation assignment:"
PRINT product
PRINT

REM Test 7: HASH_EXISTS in IGNORE_CASE mode
PRINT "HASH_EXISTS in IGNORE_CASE mode (should all PASS):"
result = HASH_EXISTS(product(), "itemname")
IF result = -1 THEN PRINT "PASS: HASH_EXISTS lowercase" ELSE PRINT "FAIL: HASH_EXISTS lowercase"

result = HASH_EXISTS(product(), "ITEMNAME")
IF result = -1 THEN PRINT "PASS: HASH_EXISTS uppercase" ELSE PRINT "FAIL: HASH_EXISTS uppercase"

result = HASH_EXISTS(product(), "ItemName")
IF result = -1 THEN PRINT "PASS: HASH_EXISTS mixed case" ELSE PRINT "FAIL: HASH_EXISTS mixed case"

result = HASH_EXISTS(product(), "nonexistent")
IF result = 0 THEN PRINT "PASS: HASH_EXISTS missing key" ELSE PRINT "FAIL: HASH_EXISTS missing key"
PRINT

PRINT "========================================"
PRINT "=== TESTING BASIC VARIABLE CASE-INSENSITIVITY ==="
PRINT "========================================"

REM Test 8: BASIC variables should always be case-insensitive
testVar = 100
check1 = testVar
check2 = TESTVAR  
check3 = TestVar
IF check1 = 100 AND check2 = 100 AND check3 = 100 THEN PRINT "PASS: BASIC variable case-insensitivity" ELSE PRINT "FAIL: BASIC variable case-insensitivity"

testString$ = "Hello World"
check1$ = testString$
check2$ = TESTSTRING$
check3$ = TestString$
IF check1$ = "Hello World" AND check2$ = "Hello World" AND check3$ = "Hello World" THEN PRINT "PASS: BASIC string variable case-insensitivity" ELSE PRINT "FAIL: BASIC string variable case-insensitivity"
PRINT

PRINT "========================================"
PRINT "=== SWITCHING BACK TO PRESERVE_CASE ==="
PRINT "========================================"

SET HASH_KEYS PRESERVE_CASE

REM Test 9: Create new hash after switching back
DIM config AS HASH
config.serverName = "localhost"
config.portNumber = 8080

PRINT "Hash created after switching back to PRESERVE_CASE:"
PRINT config
PRINT

PRINT "Dot notation access (should all PASS - always forgiving):"
result$ = config.serverName
IF result$ = "localhost" THEN PRINT "PASS: config.serverName" ELSE PRINT "FAIL: config.serverName"

result$ = config.SERVERNAME
IF result$ = "localhost" THEN PRINT "PASS: config.SERVERNAME" ELSE PRINT "FAIL: config.SERVERNAME"

result$ = config.servername
IF result$ = "localhost" THEN PRINT "PASS: config.servername" ELSE PRINT "FAIL: config.servername"
PRINT

PRINT "Bracket access (should be case-sensitive in PRESERVE_CASE):"
result$ = config("serverName")
IF result$ = "localhost" THEN PRINT "PASS: config(""serverName"")" ELSE PRINT "FAIL: config(""serverName"")"

result$ = config("SERVERNAME$")
IF result$ = "" THEN PRINT "PASS: config(""SERVERNAME"") should fail" ELSE PRINT "FAIL: config(""SERVERNAME"") found: " + result$
PRINT

PRINT "=== FINAL SUMMARY ==="
PRINT "Review results above:"
PRINT "- All dot notation should PASS (forgiving)"
PRINT "- PRESERVE_CASE bracket notation should be strict" 
PRINT "- IGNORE_CASE bracket notation should be forgiving"
PRINT "- BASIC variables should always be case-insensitive"
END