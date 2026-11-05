REM Form demo: an order entry form with a LOOKUP list, checks with messages, a field
REM that only applies to members (WHEN), and Save/Cancel buttons.
REM Keys: Tab or Enter = next field, F2 = list of products, Esc = cancel. The mouse works too.
DATABASE OPEN ":memory:"
CREATE TABLE products (code TEXT PRIMARY KEY, name TEXT, price REAL);
INSERT INTO products VALUES ('A100', 'Widget', 2.5), ('B200', 'Gadget', 10), ('C300', 'Gizmo', 99.95);

COLOR 15, 1, 0, 3
CLS
BOX 3, 10, 14, 70, "New order" DOUBLE
o.product = "" : o.qty = 1 : o.member = "N" : o.discount = 0
@ 5, 13 SAY "Product   : " GET o.product PICTURE "!!!!" LOOKUP (SELECT code, name, price FROM products ORDER BY code)
@ 6, 13 SAY "Quantity  : " GET o.qty VALID o.qty >= 1 AND o.qty <= 100 MESSAGE "Quantity must be 1 to 100"
@ 7, 13 SAY "Member?   : " GET o.member PICTURE "!" VALID o.member = "Y" OR o.member = "N" MESSAGE "Type Y or N"
@ 8, 13 SAY "Discount %: " GET o.discount WHEN o.member = "Y" VALID o.discount <= 20 MESSAGE "Members get at most 20%"
@ 10, 13 SAY "F2 on Product shows the list of products."
@ 12, 25 BUTTON "Save"
@ 12, 35 BUTTON "Cancel" CANCEL
READ

COLOR 7, 0
CLS
IF BUTTON$ = "Save" THEN
    price = (SELECT price FROM products WHERE code = :o.product)
    total = price * o.qty * (100 - o.discount) / 100
    PRINT "Order:"; o.qty; " x "; o.product; " = "; TRIM$(FORMAT$(total, "$#,##0.00"))
ELSE
    PRINT "Order cancelled."
END IF
REM EXPECT: Order: 3 x B200 = $27.00
