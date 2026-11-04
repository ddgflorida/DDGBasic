REM KILL of a missing file sets ERR = 2 and continues, unless an ON ERROR handler
REM is active, in which case the handler is called. Any failed check raises an error.
KILL "kill_missing_file.tmp"
IF ERR <> 2 THEN ERROR 1, "no handler: ERR = " + STR$(ERR)

handled = 0
ON ERROR GOTO trap
KILL "kill_missing_file.tmp"
ON ERROR GOTO 0
IF handled <> 1 THEN ERROR 1, "the ON ERROR handler was not called"

REM With the handler turned off again it is quiet once more.
KILL "kill_missing_file.tmp"
IF ERR <> 2 THEN ERROR 1, "handler off: ERR = " + STR$(ERR)

REM An existing file is deleted with ERR = 0.
OPEN "kill_test.tmp" FOR OUTPUT AS #1
PRINT #1, "x"
CLOSE #1
KILL "kill_test.tmp"
IF ERR <> 0 OR FILE_EXISTS("kill_test.tmp") THEN ERROR 1, "existing file not deleted"
PRINT "kill_errors: all checks passed"
END

trap:
handled = handled + 1
IF ERR <> 2 THEN ERROR 1, "handler: ERR = " + STR$(ERR)
RESUME NEXT
