REM --- Comprehensive PRINT USING Test ---

PRINT "--- SECTION 1: Numeric Formatting ---"
num1 = 1234.567
num2 = -78.9
num3 = 0.12

PRINT "Test 1.1: Basic number formatting with #"
PRINT USING "####.##"; num1
PRINT USING "####.##"; 88

PRINT "Test 1.2: Leading/trailing zeros with 0"
PRINT USING "00000.00"; num1
PRINT USING "##.000"; 45.6

PRINT "Test 1.3: Thousand separators"
PRINT USING "##,###,###.##"; 1234567.89
PRINT USING "##,###.##"; num1

PRINT "Test 1.4: Leading asterisks for check protection"
PRINT USING "**,###.##"; num1
PRINT USING "******.##"; 42.5

PRINT "Test 1.5: Scientific notation with ^^^^"
PRINT USING "#.##^^^^"; 123456
PRINT USING "#.##^^^^"; 0.000789

PRINT "Test 1.6: Handling negative numbers"
PRINT USING "#####.##"; num2
PRINT USING "-#####.##"; 123.45 ' Should show space
PRINT

PRINT "--- SECTION 2: String Formatting ---"
str1$ = "Hello"
str2$ = "World"

PRINT "Test 2.1: First character with !"
PRINT USING "!"; str1$

PRINT "Test 2.2: Full string with &"
PRINT USING "&"; str1$

PRINT "Test 2.3: Fixed-width fields with \\ \\"
PRINT "Left justified (default):"
PRINT USING "\         \"; str1$

PRINT "Right justified:"
PRINT USING ">\         \"; str1$

PRINT "Center justified:"
PRINT USING "^\         \"; str1$
PRINT

PRINT "--- SECTION 3: Combined Formatting ---"
item$ = "Widget"
price = 49.99
quantity = 10
PRINT USING "Item: &  Qty: ##  Price: $##.00"; item$, quantity, price
PRINT

PRINT "--- PRINT USING test complete. ---"
END
