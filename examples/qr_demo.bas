REM QR codes: a product screen with a code a phone can scan, and a printable label
REM for every product, made from a query.
REM   QR text$ AT row, col   draws a code on the screen (dark squares on white)
REM   QR text$ TO "x.png"    saves it as an image (.png or .svg) to print
REM Keys: any key shows the next product; Esc ends.
DATABASE OPEN ":memory:"
CREATE TABLE products (code TEXT PRIMARY KEY, name TEXT, price REAL, stock INTEGER);
INSERT INTO products VALUES ('A100', 'Widget', 2.5, 120), ('B200', 'Gadget', 10, 8),
    ('C300', 'Gizmo', 99.95, 0);

REM --- A label for every product, ready to print ---------------------------------
FOR p IN (SELECT code FROM products ORDER BY code)
    QR "https://shop.example.com/p/" & p.code TO "qr_label_" & p.code & ".png"
NEXT
labels = (SELECT COUNT(*) FROM products)

REM --- A product screen with its code -----------------------------------------
COLOR 15, 1, 0, 3
FOR p IN (SELECT code, name, price, stock FROM products ORDER BY code)
    CLS
    BOX 2, 2, 22, 79, "Product " & p.code
    @ 5, 6 SAY "Name  : " & p.name
    @ 6, 6 SAY "Price : " & TRIM$(FORMAT$(p.price, "$#,##0.00"))
    IF p.stock > 0 THEN stock$ = p.stock & " in stock" ELSE stock$ = "out of stock"
    @ 7, 6 SAY "Stock : " & stock$
    @ 10, 6 SAY "Scan the code with a phone"
    @ 11, 6 SAY "to open the product's page."
    @ 19, 6 SAY "Any key: next product   Esc: end"
    QR "https://shop.example.com/p/" & p.code AT 4, 44
    k$ = INKEY$(0)
    IF k$ = CHR$(27) THEN EXIT FOR
NEXT
COLOR 7, 0
CLS
PRINT labels; " labels saved: qr_label_A100.png and the others"
REM EXPECT: 3 labels saved
