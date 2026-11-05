REM FOR ... IN JSONL skips an invalid line with a warning and carries on.
REM Failed checks raise errors.
n = 0
names$ = ""
FOR rec IN JSONL("data/bad_line.jsonl")
    n = RECNO
    IF TYPENAME$(rec) = "HASH" THEN names$ = names$ & rec.name & " "
NEXT
REM EXPECT: Warning: Skipping invalid JSON on line 2 of 'data/bad_line.jsonl'
IF n <> 3 THEN ERROR 1, "RECNO should count the 3 records received, got " & STR$(n)
IF names$ <> "Ann Cy " THEN ERROR 1, "records read: " & names$
PRINT "jsonl_bad_lines: all checks passed"
REM EXPECT: jsonl_bad_lines: all checks passed
