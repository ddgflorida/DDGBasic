REM File I/O fixes: unopened handles, ERR/ERRMSG$ from OPEN errors, ~ in names,
REM WRITE # line endings, UNZIP ERR, INPUT with a comma and re-asking for numbers.
REM Input for this test is supplied by tests/run_tests.py.
REM Failed checks raise errors.
msg$ = ""
ON ERROR GOTO closed_handle
PRINT #9, "x"
GOTO after_closed
closed_handle:
msg$ = ERRMSG$
RESUME after_closed
after_closed:
ON ERROR GOTO 0
IF INSTR(msg$, "File #9 is not open") = 0 THEN ERROR 1, "closed handle message: " + msg$

MKDIR "fio_dir"
ON ERROR GOTO dir_error
OPEN "fio_dir" FOR INPUT AS #1
GOTO after_dir
dir_error:
code = ERR
RESUME after_dir
after_dir:
ON ERROR GOTO 0
IF code <> 1 THEN ERROR 1, "OPEN of a directory: ERR = " + STR$(code)
RMDIR "fio_dir"

OPEN "~/ddgbasic_fio_test.tmp" FOR OUTPUT AS #1
WRITE #1, "a", 1
PRINT #1, "b"
CLOSE #1
NAME "~/ddgbasic_fio_test.tmp" AS "~/ddgbasic_fio_test2.tmp"
READ FILE "~/ddgbasic_fio_test2.tmp" INTO f$
KILL "~/ddgbasic_fio_test2.tmp"
IF INSTR(f$, CHR$(13)) THEN ERROR 1, "WRITE # and PRINT # line endings differ"

SET SQL_FATAL_ERRORS OFF
UNZIP "no_such_archive.zip" TO "fio_out"
IF ERR <> 2 THEN ERROR 1, "UNZIP missing archive: ERR = " + STR$(ERR)
SET SQL_FATAL_ERRORS ON

INPUT "Name", n$
INPUT "Age"; age
IF n$ <> "Ann" OR age <> 42 THEN ERROR 1, "INPUT got [" + n$ + "] " + STR$(age)
PRINT
PRINT "file_io_fixes: all checks passed"
