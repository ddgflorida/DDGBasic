ON ERROR GOTO Handler
OpenFile:
	INPUT "Name of file to update: ";FileSpec$
	IF FileSpec$ = "" THEN END
	OPEN FileSpec$ FOR INPUT AS #1
	PRINT "The first five lines of ";FILESPEC$;" are:" : PRINT
	FOR I = 1 TO 5
		LINE INPUT #1, Temp$
		PRINT Temp$
	NEXT
	PRINT 
	INPUT "Is this the correct file [? yn] ";R$
	REM Define error 200.
	IF LEFT$(R$,1) <> "y" THEN ERROR 200, "Oops, wrong file."
	END

Handler:        REM Error-handling routine.
	Number = ERR
	REM Run-time error for "file not found."
	IF Number = 2 THEN
		PRINT "File not in this directory"
		PRINT "Enter new file spec ([d:]xxx...xxx) or"
		PRINT "press <RETURN> to end program"
		RESUME OpenFile
	ELSEIF Number = 200 THEN
REM User entered "n"
		CLOSE #1
		RESUME OpenFile
	ELSE
		ERROR Number       REM Error other than 53 or 200.
		ON ERROR GOTO 0    REM Print message, disable error
	END IF                     REM handling, and stop program.