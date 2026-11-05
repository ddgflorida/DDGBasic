REM An unknown SET option is an error; a successful LOAD resets ERR to 0.
REM Any failed check raises an error (exit 1).
trapped = 0
ON ERROR GOTO bad_set
SET no_such_option = 5
GOTO after_set
bad_set:
trapped = 1
RESUME after_set
after_set:
ON ERROR GOTO 0
IF trapped <> 1 THEN ERROR 1, "unknown SET option was not rejected"

KILL "no_such_file.tmp"
IF ERR <> 2 THEN ERROR 1, "setup: KILL should leave ERR = 2"
DATABASE OPEN ":memory:"
LOAD CSV "data/tiny.csv" CREATE TABLE t OPTIONS "header=true"
IF ERR <> 0 THEN ERROR 1, "successful LOAD left ERR = " + STR$(ERR)
PRINT "set_and_load_err: all checks passed"
