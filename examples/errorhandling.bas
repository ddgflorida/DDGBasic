REM Error handling with ON ERROR GOTO and RESUME, in the style of the classic BASIC manuals.
REM The program asks for a file and shows its first five lines. A missing file (ERR = 2) and
REM the program's own error 200 ("wrong file") are handled by asking again. Any other error
REM is passed on with ERROR, which stops the program with that error's number and message.
ON ERROR GOTO handler

open_file:
    INPUT "Name of file to show (Enter to quit): "; file_spec$
    IF file_spec$ = "" THEN END
    OPEN file_spec$ FOR INPUT AS #1
    PRINT "The first five lines of "; file_spec$; " are:"
    PRINT
    FOR i = 1 TO 5
        LINE INPUT #1, text$
        PRINT text$
    NEXT
    PRINT
    INPUT "Is this the right file (y/n)? "; answer$
    IF LEFT$(LCASE$(answer$), 1) <> "y" THEN ERROR 200, "Wrong file"
    CLOSE #1
    PRINT "Done."
    END

handler:
    REM ERR says which error happened
    IF ERR = 2 THEN
        REM File not found: say so and ask again
        PRINT "There is no file called "; file_spec$; "."
        RESUME open_file
    ELSEIF ERR = 200 THEN
        REM The user answered "n": close the file and ask again
        CLOSE #1
        RESUME open_file
    ELSE
        REM Any other error: pass it on. Errors inside a handler are not trapped,
        REM so ERROR stops the program here with this error's number and message.
        ERROR ERR, ERRMSG$
    END IF

REM The test runner types a missing file name, then Enter to quit, and checks for:
REM EXPECT: There is no file called nope.txt.
