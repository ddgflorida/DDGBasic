DIM data AS HASH
json$ = "{""name"":""John"",""age"":30,""scores"":[95,87,92]}"
data = PARSEJSON(json$)

PRINT "Name: "; data.name
PRINT "Age: "; data.age
PRINT "First score: "; data.scores(0)