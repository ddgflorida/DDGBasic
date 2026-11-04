REM Used by tests/functions_across_programs.bas (CHAIN target).
FUNCTION greet$(n$)
  greet$ = "hi " + n$
END FUNCTION
IF greet$("bob") <> "hi bob" THEN ERROR 1, "CHAIN target: own function failed"
PRINT "functions_across_programs: all checks passed"
