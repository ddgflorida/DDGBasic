REM FILE OPERATIONS
ON ERROR GOTO fileerr

REM Create and Rename File
PRINT "Creating temp.txt file"
OPEN "temp.txt" FOR OUTPUT AS #1
CLOSE

PRINT
PRINT "Running dir *txt"
SHELL "dir *.txt"
REM Rename file
PRINT
PRINT "Renaming file temp.txt as data.txt"
NAME "temp.txt" AS "data.txt"
PRINT

PRINT "Running dir *txt"
SHELL "dir *.txt"
PRINT
PRINT "Removing data.txt"
REM Delete file
KILL "data.txt"
PRINT
PRINT "Running dir *txt"
SHELL "dir *.txt"

REM Directory operations
PRINT "Directory operations:"
PRINT "Making directory backups"
MKDIR "backups"

PRINT "Changing directory to folder backups"
CHDIR "backups"
current$ = CURDIR$
PRINT "Current directory: "; current$
PRINT
PRINT "Changing directory 1 level up .."
CHDIR ".."
PRINT "Removing directory backups"
RMDIR "backups"
PRINT "FILE OPERATIONS Completed Successfully"
END

fileerr:
REM Check for errors
IF ERR <> 0 THEN
    PRINT "File operation failed"
END IF