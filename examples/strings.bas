REM String manipulation
name$ = "  John Doe  "
clean$ = TRIM$(name$)
first$ = LEFT$(clean$, 4)       REM "John"
last$ = RIGHT$(clean$, 3)       REM "Doe"
middle$ = MID$(clean$, 6, 3)    REM "Doe"

REM Case conversion
upper$ = UCASE$(clean$)         REM "JOHN DOE"
lower$ = LCASE$(clean$)         REM "john doe"

REM String concatenation
full$ = first$ + " " + last$
greeting$ = "Hello, " + full$ + "!"

REM String to number conversion
price$ = "29.99"
tax_rate$ = "0.08"
price_num = VAL(price$)
tax_num = VAL(tax_rate$)
total = price_num * (1 + tax_num)
PRINT "Total: $"; STR$(total)

REM Number formatting
n = 255
PRINT "Decimal: "; n
PRINT "Hex: "; HEX$(n)      REM "ff"
PRINT "Octal: "; OCT$(n)    REM "377"

REM Padding with spaces
label$ = "Name:"
value$ = "John"
PRINT label$; SPACE$(10 - LEN(label$)); value$

REM SQL String
SELECT 'Hello World';
