REM --- Test LOAD JSON Command ---

REM Step 1: Create a sample JSON file to load
OPEN "inventory.json" FOR OUTPUT AS #1
PRINT #1, "["
PRINT #1, "  {""id"": 101, ""product"": ""Widget"", ""quantity"": 50},"
PRINT #1, "  {""id"": 102, ""product"": ""Gadget"", ""quantity"": 75, ""notes"": ""On sale""},"
PRINT #1, "  {""id"": 103, ""product"": ""Thingamajig"", ""quantity"": 20}"
PRINT #1, "]"
CLOSE #1

PRINT "--- 1. Loading inventory.json into database ---"
DATABASE OPEN ":memory:"
LOAD JSON "inventory.json" CREATE TABLE "inventory"
IF ERR <> 0 THEN
    PRINT "Error loading JSON: "; ERRMSG$
    END
END IF
PRINT

PRINT "--- 2. Verifying loaded data ---"
SELECT id, product, quantity, notes FROM inventory;
PRINT

REM --- Cleanup ---
KILL "inventory.json"
DATABASE CLOSE
END