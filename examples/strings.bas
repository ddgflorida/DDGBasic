REM String manipulation
name$ = "  John Doe  "
clean$ = TRIM$(name$)
first$ = LEFT$(clean$, 4)       ' "John"
last$ = RIGHT$(clean$, 3)       ' "Doe"
middle$ = MID$(clean$, 6, 3)    ' "Doe"

' Case conversion
upper$ = UCASE$(clean$)         ' "JOHN DOE"
lower$ = LCASE$(clean$)         ' "john doe"

' String concatenation
full$ = first$ + " " + last$
greeting$ = "Hello, " + full$ + "!"

' String to number conversion
price$ = "29.99"
tax_rate$ = "0.08"
price_num = VAL(price$)
tax_num = VAL(tax_rate$)
total = price_num * (1 + tax_num)
PRINT "Total: $"; STR$(total)

' Number formatting
n = 255
PRINT "Decimal: "; n
PRINT "Hex: "; HEX$(n)      ' "ff"
PRINT "Octal: "; OCT$(n)    ' "377"

' Padding with spaces
label$ = "Name:"
value$ = "John"
PRINT label$; SPACE$(10 - LEN(label$)); value$