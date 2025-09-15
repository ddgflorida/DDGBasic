REM --- Comprehensive PRINT Statement Test ---

PRINT "--- SECTION 1: Basic PRINT Functionality ---"
PRINT "This is a string literal."
PRINT 123.45
x = 99
PRINT "The value of x is"; x
PRINT ' This should print a blank line

PRINT "--- SECTION 2: Comma and Semicolon Separators ---"
PRINT "Comma,", "separated,", "output."
PRINT "Semicolon;" ; "separated;" ; "output."
PRINT "This line will";
PRINT " continue." ' Semicolon at the end suppresses the newline
PRINT

PRINT "--- SECTION 3: Printing Expressions and Functions ---"
PRINT "The result of 10 + 20 is"; 10 + 20
PRINT "The length of 'hello' is "; LEN("hello")
PRINT

PRINT "--- SECTION 4: Printing to a File ---"
OPEN "print_test.txt" FOR OUTPUT AS #1
PRINT #1, "This line goes to the file."
PRINT #1, "Value 1", "Value 2"
CLOSE #1

PRINT "Content of 'print_test.txt':"
READ FILE "print_test.txt" INTO file_content$
PRINT file_content$
KILL "print_test.txt"
PRINT

PRINT "--- SECTION 5: Printing Collections ---"
DIM my_array()
my_array = SPLIT("one,two,three", ",")
PRINT "Printing an array:"; my_array

DIM my_hash AS HASH
my_hash.name = "Alice"
my_hash.age = 30
PRINT "Printing a hash:"; my_hash
PRINT

PRINT "--- PRINT test complete. ---"
END
