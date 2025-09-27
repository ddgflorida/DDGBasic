DIM person AS HASH
person.name = "Alice"
person.age = 25
person.active = 1

REM Keys from HASH's are uppercase.
json$ = JSON_SERIALIZE$(person)
PRINT json$  REM  {"NAME":"Alice","AGE":25,"active":1}

REM Save to file
OPEN "person.json" FOR OUTPUT AS #1
PRINT #1, json$
CLOSE #1
PRINT "person.json file created"