REM --- Test script for FOR EACH...IN HASH loop ---

PRINT "--- 1. Initializing HASH variable ---"
DIM person AS HASH
person("Name") = "Alice"
person("Level") = 12
person("Class") = "Mage"
PRINT "-> HASH created."
PRINT

PRINT "--- 2. Iterating with FOR EACH...LOOP ---"
FOR EACH key$ IN HASH person
    PRINT "  Key: "; key$; " -> Value: "; person(key$)
NEXT
PRINT "-> Iteration complete."
PRINT

END