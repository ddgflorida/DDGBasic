REM Used by tests/functions_across_programs.bas (RUN target).
FUNCTION triple(x)
  triple = x * 3
END FUNCTION
IF triple(4) <> 12 THEN ERROR 1, "RUN child: own function failed"
IF double(4) <> 8 THEN ERROR 1, "RUN child: caller's function failed"
