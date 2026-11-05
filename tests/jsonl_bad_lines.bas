REM FOR ... IN JSONL skips an invalid line with a warning and carries on.
REM Failed checks raise errors.
lines$ = ""
names$ = ""
FOR rec IN JSONL("data/bad_line.jsonl")
    lines$ = lines$ & STR$(RECNO)
    IF TYPENAME$(rec) = "HASH" THEN names$ = names$ & rec.name & " "
NEXT
REM EXPECT: Warning: Skipping invalid JSON on line 2 of 'data/bad_line.jsonl'
IF lines$ <> " 1 4 5" THEN ERROR 1, "RECNO should be the file line numbers 1 4 5, got" & lines$
IF names$ <> "Ann Cy " THEN ERROR 1, "records read: " & names$
PRINT "jsonl_bad_lines: all checks passed"
REM EXPECT: jsonl_bad_lines: all checks passed
