' Create and Rename File
OPEN "temp.txt" FOR OUTPUT AS #1
CLOSE
SHELL "dir *.txt"
' Rename file
NAME "temp.txt" AS "data.txt"
SHELL "dir *.txt"
REM Delete file
KILL "data.txt"
SHELL "dir *.txt"

' Directory operations
PRINT "Directory operations"
MKDIR "backups"
CHDIR "backups"
current$ = CURDIR$
PRINT "Current directory: "; current$
CHDIR ".."
RMDIR "backups"

' Check for errors
IF ERR <> 0 THEN
    PRINT "File operation failed"
END IF