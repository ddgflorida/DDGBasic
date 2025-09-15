REM --- SORT Command Examples ---

REM --- Example 1: Sorting an array of hashes ---
PRINT "--- 1. Sorting an array of HASHes ---"
DIM people AS ARRAY
DIM person AS HASH

person("NAME") = "Jane"
person("AGE") = 32
people(0) = person

DIM person AS HASH
person("NAME") = "John"
person("AGE") = 45
people(1) = person

DIM person AS HASH
person("NAME") = "Alice"
person("AGE") = 28
people(2) = person

PRINT "Original array:"
PRINT JSON_SERIALIZE$(people, 2)
PRINT ""

PRINT "Sorted by NAME ASC:"
SORT people ON "NAME"
PRINT JSON_SERIALIZE$(people, 2)
PRINT

PRINT "Sorted by AGE DESC:"
SORT people ON "AGE" DESC
PRINT JSON_SERIALIZE$(people, 2)
PRINT ""

REM --- Example 2: Sorting an array of simple values ---
PRINT "--- 2. Sorting a simple array ---"
DIM numbers AS ARRAY
numbers(0) = 100
numbers(1) = 50
numbers(2) = 250
numbers(3) = 10

PRINT "Original numbers:"
PRINT numbers
PRINT

PRINT "Sorted numbers ASC:"
SORT numbers
PRINT numbers
PRINT

PRINT "Sorted numbers DESC:"
SORT numbers DESC
PRINT numbers
PRINT

END