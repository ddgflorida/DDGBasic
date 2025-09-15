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
	'Define error 200.
	IF LEFT$(R$,1) <> "y" THEN ERROR 200, "Oops, wrong file."
	END

Handler:        'Error-handling routine.
	Number = ERR
	' Run-time error for "file not found."
	IF Number = 2 THEN
		PRINT "File not in this directory"
		PRINT "Enter new file spec ([d:]xxx...xxx) or"
		PRINT "press <RETURN> to end program"
		RESUME OpenFile
	ELSEIF Number = 200 THEN
'User entered "n"
		CLOSE #1
		RESUME OpenFile
	ELSE
		ERROR Number       'Error other than 53 or 200.
		ON ERROR GOTO 0    'Print message, disable error
	END IF                 'handling, and stop program.