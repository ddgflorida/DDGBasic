REM --- Comprehensive Subquery Test Suite ---

PRINT "--- SECTION 1: Subqueries without Tables ---"
REM Test 1.1: Simple math in a LET statement
LET result = (SELECT 10 * 5)
PRINT "Test 1.1: (SELECT 10 * 5) ="; result
IF result = 50 THEN
PRINT "-> PASSED"
ELSE
PRINT "-> FAILED"
END IF
PRINT

REM Test 1.2: Simple comparison in an IF statement
IF (SELECT 100) > 50 THEN
PRINT "Test 1.2: (SELECT 100) > 50 is TRUE"
PRINT "-> PASSED"
ELSE
PRINT "Test 1.2: (SELECT 100) > 50 is FALSE"
PRINT "-> FAILED"
END IF
PRINT

REM --- SECTION 2: Subqueries with a temporary table ---
PRINT "--- SECTION 2: Subqueries with a Table ---"
DATABASE OPEN ":memory:"
CREATE TABLE products (id INTEGER, name TEXT, price REAL);
INSERT INTO products VALUES (1, 'Gadget', 19.99);
INSERT INTO products VALUES (2, 'Widget', 24.50);
INSERT INTO products VALUES (3, 'Doodad', 9.95);
PRINT "-> Temporary 'products' table created and populated."
PRINT

REM Test 2.1: Get record count with LET
LET product_count = (SELECT COUNT() FROM products)
PRINT "Test 2.1: (SELECT COUNT()) ="; product_count
IF product_count = 3 THEN
PRINT "-> PASSED"
ELSE
PRINT "-> FAILED"
END IF
PRINT

REM Test 2.2: Use record count in an IF statement
IF (SELECT COUNT(*) FROM products WHERE price > 10) = 2 THEN
    PRINT "Test 2.2: Correctly found 2 products with price > 10"
    PRINT "-> PASSED"
ELSE
    PRINT "Test 2.2: Failed to find products with price > 10"
    PRINT "-> FAILED"
END IF
PRINT
PRINT "PRODUCTS TABLE:"
SELECT name FROM products;
PRINT

REM Test 2.3: Get a string value with LET
LET item_name$ = (SELECT name FROM products WHERE id = 2)
PRINT "Test 2.3: Fetched name for ID 2 is '"; item_name$; "'"
IF item_name$ = "Widget" THEN
    PRINT "-> PASSED"
ELSE
    PRINT "-> FAILED (Note: String results from DB are uppercase)"
END IF
PRINT

REM Test 2.4: EXISTS CLAUSE
PRINT " Test 2.4: EXISTS CLAUSE"
IF EXISTS(SELECT name FROM products WHERE id = 2) THEN
    PRINT "-> PASSED"
ELSE
    PRINT "-> FAILED: EXISTS failed to find id = 2"
END IF
PRINT

REM --- SECTION 3: Intentional Failure Test ---
PRINT "--- SECTION 3: Testing Error Handling ---"
PRINT "The next test is EXPECTED to fail."
PRINT "It tests if the interpreter correctly rejects a subquery that returns more than one value."
REM This line should raise an error, which the handler below reports as a pass.
ON ERROR GOTO expected_failure
LET bad_result = (SELECT name FROM products)
PRINT "-> FAILED: This line should not be reached. The query should have caused an error."
END

expected_failure:
PRINT "-> PASSED: "; ERRMSG$
END