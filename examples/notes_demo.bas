REM Notes demo: EDIT TEXT edits a note, VIEW shows it (and a file) with search.
REM EDIT TEXT keys: Enter splits a line, Ctrl-Y deletes a line, Ctrl-W saves, Esc cancels.
REM VIEW keys: arrows scroll, / finds, n finds the next, q closes.
notes$ = "Meeting notes" + CHR$(10) + "- call ACME about the order" + CHR$(10) + "- send the report"
COLOR 15, 1
CLS
@ 1, 2 SAY "Edit the note, then press Ctrl-W to save it."
EDIT TEXT notes$ AT 3, 5, 15, 75 TITLE "Notes"
VIEW notes$ AT 3, 5, 15, 75 TITLE "Your note"

OPEN "note.txt" FOR OUTPUT AS #1
PRINT #1, notes$
CLOSE #1
VIEW FILE "note.txt"

COLOR 7, 0
CLS
PRINT "The note has"; UBOUND(SPLIT(notes$, CHR$(10))) + 1; " lines."
REM EXPECT: The note has 4 lines.
