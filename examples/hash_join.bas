REM A quick example of HASH_JOIN

REM Define two hashes
DIM h1 AS HASH
DIM h2 AS HASH

REM Populate the first hash
h1("ID") = 123
h1("STATUS") = "ACTIVE"

REM Populate the second hash
REM Note the STATUS key overlaps with h1
h2("NAME") = "Example Item"
h2("STATUS") = "INACTIVE"

PRINT "--- Before Join ---"
PRINT "h1:"
PRINT h1
PRINT "h2:"
PRINT h2
PRINT

REM Join h1 and h2 into a new hash, h3
DIM h3 AS HASH
h3 = HASH_JOIN(h1, h2)

PRINT "--- After Join ---"
PRINT "h3:"
PRINT h3
PRINT

REM Notice that the "STATUS" value from h2
REM overwrote the value from h1.

END