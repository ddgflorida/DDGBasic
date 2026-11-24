REM QR codes: QR text$ (printed), AT row, col (on the screen), TO file (.png or .svg),
REM and QR$(text$) as lines of text. The codes themselves are checked by decoding them
REM in development; here the statements, files and errors are checked.

REM 1. QR$: lines of half blocks, two rows of squares per line, with a margin
t$ = QR$("A100 Widget 2.50")
lines = SPLIT(t$, CHR$(10))
IF ARRAY_SIZE(lines) <> 13 THEN ERROR 1, "1a: lines " & ARRAY_SIZE(lines)
IF LEN(lines(0)) <> 25 THEN ERROR 1, "1b: width " & LEN(lines(0))
IF TRIM$(lines(0)) <> "" OR INSTR(lines(1), "█") = 0 THEN ERROR 1, "1c: margin and finder pattern"

REM 2. Saved as images
QR "https://shop.example.com/p/A100" TO "code.png"
QR "https://shop.example.com/p/A100" TO "code.svg"
IF NOT FILE_EXISTS("code.png") OR FILESIZE("code.png") < 100 THEN ERROR 1, "2a: png"
READ FILE "code.svg" INTO svg$
IF INSTR(svg$, "<svg") = 0 THEN ERROR 1, "2b: svg"

REM 3. Errors: an unknown file type, and a code too big for the screen
ON ERROR GOTO caught
msg$ = ""
QR "x" TO "code.jpg"
IF INSTR(msg$, ".png or .svg") = 0 THEN ERROR 1, "3a: " & msg$
msg$ = ""
QR REPEAT$("long text ", 40) AT 1, 1
IF INSTR(msg$, "Save it to a file instead") = 0 THEN ERROR 1, "3b: " & msg$
ON ERROR GOTO 0

REM 4. On the screen: drawn at the position, and kept in the screen copy
CLS
before$ = SAVESCREEN()
QR "hello" AT 3, 10
IF SAVESCREEN() = before$ THEN ERROR 1, "4: nothing drawn"
COLOR 7, 0
CLS
PRINT "qr: all checks passed"
REM EXPECT: qr: all checks passed
END

caught:
    msg$ = ERRMSG$
    RESUME NEXT
