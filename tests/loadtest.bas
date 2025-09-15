REM --- Create a sample CSV with headers and intro lines ---
OPEN "customers_part1.csv" FOR OUTPUT AS #1
PRINT #1, "Customer Report"
PRINT #1, "Generated: "; DATE$
PRINT #1, "ID,Name,City"
PRINT #1, "101,Alice Smith,New York"
PRINT #1, "102,Bob Johnson,Chicago"
CLOSE #1

REM --- Create another CSV with no headers, using a semicolon delimiter ---
OPEN "customers_part2.csv" FOR OUTPUT AS #1
PRINT #1, "103;Charlie Brown;Los Angeles"
PRINT #1, "104;Diana Prince;Washington"
CLOSE #1

REM --- Open a database connection ---
DATABASE OPEN ":memory:"

REM --- Create a new table, skipping the first 2 lines and using the 3rd as a header ---
PRINT "Creating and loading initial customer data..."
LOAD CSV "customers_part1.csv" CREATE "customers" OPTIONS "header=true skip=2"
IF ERR <> 0 THEN PRINT "Load failed!": END

REM --- Append data from the second, headerless, semicolon-delimited file ---
PRINT "Appending more customer data..."
LOAD CSV "customers_part2.csv" INTO "customers" APPEND OPTIONS "delimiter=;"
IF ERR <> 0 THEN PRINT "Append failed!": END

PRINT
PRINT "--- Final Customer Table (first 3 rows) ---"
FOR rec IN(SELECT id,name,city FROM customers ORDER BY ID LIMIT 3) 
    PRINT rec.id, rec.name$, rec.city
NEXT

PRINT "Cleaning up"
DATABASE CLOSE
KILL "customers_part1.csv"
KILL "customers_part2.csv"
