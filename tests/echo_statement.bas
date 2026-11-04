REM ECHO prints the rest of its line as written. Only the whole word ECHO
REM starts an ECHO statement: names such as echo_count or echoes$ are variables.
REM Any failed check raises an error (exit 1).
echo_count = 5
echoes$ = "x"
IF echo_count <> 5 THEN ERROR 1, "echo_count was rewritten"
IF echoes$ <> "x" THEN ERROR 1, "echoes$ was rewritten"
ECHO echo statement: "quotes", semicolons; and $ signs
PRINT "echo_statement: all checks passed"
