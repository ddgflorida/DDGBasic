database engine duckdb
REM --- Test LOAD JSON Command ---
PRINT "Step 1: Create file inventory.json and include JSON array"
REM Step 1: Create a sample JSON file to load
OPEN "inventory.json" FOR OUTPUT AS #1
PRINT #1, "["
PRINT #1, "  {""id"": 101, ""product"": ""Widget"", ""quantity"": 50},"
PRINT #1, "  {""id"": 102, ""product"": ""Gadget"", ""quantity"": 75, ""notes"": ""On sale""},"
PRINT #1, "  {""id"": 103, ""product"": ""Thingamajig"", ""quantity"": 20}"
PRINT #1, "]"
CLOSE #1
REM
PRINT
PRINT "inventory.json:"
READ FILE "inventory.json" into f$
PRINT f$
PRINT
PRINT "Step 2: Loading inventory.json into database ---"
DATABASE OPEN ":memory:"
LOAD JSON "inventory.json" CREATE TABLE "inventory" OPTIONS "transform=product:upper"
IF ERR <> 0 THEN
    PRINT "Error loading JSON: "; ERRMSG$
    END
END IF
PRINT

PRINT "Step 3. Verifying loaded data ---"
SELECT id, product, quantity, notes FROM inventory;
PRINT

REM --- Cleanup ---
PRINT "Remove file and close database"
KILL "inventory.json"

INPUT "Press a key to edit data: "; s$
GRIDEDIT "inventory"
DATABASE CLOSE
END