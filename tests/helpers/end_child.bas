REM Used by tests/end_statement.bas (RUN target): END here must return to the caller.
child_ran = 1
IF 1 THEN END
ERROR 1, "statement after END in the RUN child was executed"
