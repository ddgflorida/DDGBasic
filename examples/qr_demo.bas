REM QR codes for retail: a product screen with a code a phone or checkout scanner can
REM read, and a printable label for every product, made from a query.
REM   Each product has a UPC-A code; upc_check$ works out its check digit and
REM   gtin_valid tests a code typed or scanned in, the way a checkout does.
REM   The QR code holds a GS1 Digital Link, the format retailers are moving to (GS1
REM   "Sunrise 2027"): one web address with the GTIN, the lot and the expiry date,
REM   that a phone opens as a web page and a checkout reads as the product code.
REM   QR text$ AT row, col   draws a code on the screen (dark squares on white)
REM   QR text$ TO "x.png"    saves it as an image (.png or .svg) to print
REM Keys: any key shows the next product; Esc ends.

REM The check digit of a GTIN (UPC-A, EAN-13, ...) from its other digits: from the
REM right, the digits are weighted 3, 1, 3, 1, ...; the check digit brings the total
REM up to a multiple of 10.
FUNCTION gtin_check$(digits$)
    DIM total, weight, i
    total = 0
    weight = 3
    FOR i = LEN(digits$) TO 1 STEP -1
        total = total + VAL(MID$(digits$, i, 1)) * weight
        weight = 4 - weight
    NEXT
    gtin_check$ = TRIM$(STR$(MOD(10 - MOD(total, 10), 10)))
END FUNCTION

REM A whole UPC-A: the 11 digits and their check digit
FUNCTION upc_check$(digits$)
    upc_check$ = digits$ & gtin_check$(digits$)
END FUNCTION

REM True when code$ is a GTIN-8, -12 (UPC-A), -13 or -14 with the right check digit
FUNCTION gtin_valid(code$)
    DIM n
    n = LEN(code$)
    gtin_valid = 0
    IF NOT ISDIGIT(code$) THEN EXIT FUNCTION
    IF n <> 8 AND n <> 12 AND n <> 13 AND n <> 14 THEN EXIT FUNCTION
    gtin_valid = (RIGHT$(code$, 1) = gtin_check$(LEFT$(code$, n - 1)))
END FUNCTION

REM A GS1 Digital Link: domain/01/GTIN-14/10/lot?17=expiry. The GTIN is padded to 14
REM digits; the expiry date (YYYY-MM-DD) is written as YYMMDD.
FUNCTION gs1_link$(domain$, gtin$, lot$, expiry$)
    DIM yymmdd$
    yymmdd$ = MID$(expiry$, 3, 2) & MID$(expiry$, 6, 2) & MID$(expiry$, 9, 2)
    gs1_link$ = domain$ & "/01/" & PADLEFT$(gtin$, 14, "0") _
        & "/10/" & REPLACE$(URLENCODE$(lot$), "+", "%20") & "?17=" & yymmdd$
END FUNCTION

REM A UPC as it is printed under the bars: 0 12345 00001 0
FUNCTION upc_text$(upc$)
    upc_text$ = LEFT$(upc$, 1) & " " & MID$(upc$, 2, 5) & " " & MID$(upc$, 7, 5) & " " & RIGHT$(upc$, 1)
END FUNCTION

REM What a checkout would say about a code typed or scanned in
FUNCTION show_check(code$)
    IF gtin_valid(code$) THEN
        PRINT code$; ": a valid UPC"
    ELSE
        PRINT code$; ": not a valid UPC (a wrong check digit or length)"
    END IF
END FUNCTION

DATABASE OPEN ":memory:"
REM upc holds the first 11 digits; the check digit is worked out from them
CREATE TABLE products (code TEXT PRIMARY KEY, upc TEXT, name TEXT, price REAL, stock INTEGER,
    lot TEXT, expiry TEXT);
INSERT INTO products VALUES
    ('A100', '01234500001', 'Widget', 2.5, 120, 'L2611A', '2027-06-30'),
    ('B200', '01234500002', 'Gadget', 10, 8, 'L2611B', '2027-12-31'),
    ('C300', '01234500003', 'Gizmo', 99.95, 0, 'L2512C', '2026-12-15');
domain$ = "https://example.com"

REM --- A label for every product, ready to print ---------------------------------
FOR p IN (SELECT code, upc, lot, expiry FROM products ORDER BY code)
    QR gs1_link$(domain$, upc_check$(p.upc), p.lot, p.expiry) TO "qr_label_" & p.code & ".png"
NEXT
labels = (SELECT COUNT(*) FROM products)

REM --- A product screen with its code -----------------------------------------
COLOR 15, 1, 0, 3
FOR p IN (SELECT code, upc, name, price, stock, lot, expiry FROM products ORDER BY code)
    upc$ = upc_check$(p.upc)
    CLS
    BOX 2, 2, 22, 79, "Product " & p.code
    @ 4, 5 SAY "Name   : " & p.name
    @ 5, 5 SAY "Price  : " & TRIM$(FORMAT$(p.price, "$#,##0.00"))
    IF p.stock > 0 THEN stock$ = p.stock & " in stock" ELSE stock$ = "out of stock"
    @ 6, 5 SAY "Stock  : " & stock$
    @ 8, 5 SAY "UPC    : " & upc_text$(upc$)
    @ 9, 5 SAY "GTIN-14: " & PADLEFT$(upc$, 14, "0")
    @ 10, 5 SAY "Lot    : " & p.lot
    @ 11, 5 SAY "Expiry : " & p.expiry
    @ 14, 5 SAY "The code holds the GTIN, lot and"
    @ 15, 5 SAY "expiry: a phone opens the product"
    @ 16, 5 SAY "page, a checkout reads the GTIN."
    @ 20, 5 SAY "Any key: next   Esc: end"
    QR gs1_link$(domain$, upc$, p.lot, p.expiry) AT 3, 41
    k$ = INKEY$(0)
    IF k$ = CHR$(27) THEN EXIT FOR
NEXT
COLOR 7, 0
CLS
PRINT labels; " labels saved: qr_label_A100.png and the others"
REM EXPECT: 3 labels saved

REM --- Checking codes typed or scanned in ------------------------------------
PRINT "Label A100 holds "; gs1_link$(domain$, upc_check$("01234500001"), "L2611A", "2027-06-30")
REM EXPECT: https://example.com/01/00012345000010/10/L2611A?17=270630
show_check("012345000010")
show_check("012345000019")
show_check("0123450000")
REM EXPECT: 012345000010: a valid UPC
REM EXPECT: 012345000019: not a valid UPC
