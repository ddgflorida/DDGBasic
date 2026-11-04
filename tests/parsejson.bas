DIM data AS HASH
json$ = "{""name"":""John"",""age"":30,""scores"":[95,87,92]}"
data = PARSEJSON(json$)

PRINT "Name: "; data.name
PRINT "Age: "; data.age
PRINT "First score: "; data.scores(0)

REM Checks (any failure raises an error, exit 1)
IF data.name <> "John" THEN ERROR 1, "PARSEJSON name"
IF data.scores(2) <> 92 THEN ERROR 1, "PARSEJSON array element"
REM PARSE is not a keyword (there is no PARSE JSON statement), so it can be a variable name
parse = 1
IF parse <> 1 THEN ERROR 1, "parse as a variable"
PRINT "parsejson: all checks passed"
