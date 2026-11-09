REM Numeric fields with a mask: typing a digit first starts a new number (calculator
REM style); an arrow key first edits the number as text; Backspace first removes one
REM digit. Keys come from the test runner's STDIN.
COLOR 15, 1
CLS
amount = 1250.5 : qty = 1250 : price = 99 : limit = 1.5
@ 3, 5 SAY "Amount: " GET amount PICTURE "99,999.99"
@ 4, 5 SAY "Qty   : " GET qty PICTURE "9999"
@ 5, 5 SAY "Price : " GET price PICTURE "999"
@ 6, 5 SAY "Limit : " GET limit PICTURE "99.9"
REM Keys: Left x5, Del, "9", Enter -> 1,290.50
REM       Backspace, Enter -> 125
REM       "7", Enter -> 7
REM       End "2" Enter (refused: more decimals than the mask), Backspace Backspace "9" Enter -> 1.9
READ
COLOR 7, 0
CLS
IF amount <> 1290.5 THEN ERROR 1, "arrows then Del and a digit: " & STR$(amount)
IF qty <> 125 THEN ERROR 1, "Backspace first: " & STR$(qty)
IF price <> 7 THEN ERROR 1, "a digit first replaces: " & STR$(price)
IF limit <> 1.9 THEN ERROR 1, "decimals beyond the mask: " & STR$(limit)
PRINT "numeric_edit: all checks passed"
REM EXPECT: numeric_edit: all checks passed
