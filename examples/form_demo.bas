REM Form demo: an order entry form with a LOOKUP list, a check box, a drop-down list,
REM a date, number masks, checks with messages, a field that only applies to members (WHEN),
REM a note for the order,
REM Save/Cancel buttons, and F1 help that works anywhere (ON KEY).
REM Keys: Tab or Enter = next field, F2 = list, Space = tick a box or open a list,
REM F1 = help, Esc = cancel. The mouse works too.
DATABASE OPEN ":memory:"
CREATE TABLE products (code TEXT PRIMARY KEY, name TEXT, price REAL);
INSERT INTO products VALUES ('A100', 'Widget', 2.5), ('B200', 'Gadget', 10), ('C300', 'Gizmo', 99.95);

FUNCTION show_help()
    BOX 6, 18, 15, 62, "Help" DOUBLE SHADOW
    @ 8, 21 SAY "Tab, Enter  next field"
    @ 9, 21 SAY "Shift-Tab   previous field"
    @ 10, 21 SAY "F2, Space   open a list / tick a box"
    @ 11, 21 SAY "Ctrl-Y      clear a field"
    @ 12, 21 SAY "Esc         cancel the order"
    @ 13, 21 SAY "Press a key..."
    k$ = INKEY$(0)
END FUNCTION
ON KEY "F1" CALL show_help

COLOR 15, 1, 0, 3
CLS
BOX 2, 10, 19, 70, "New order" DOUBLE
o.product = "" : o.qty = 1 : o.member = "N" : o.discount = 0
o.ship = "" : o.state = "FL" : o.phone = "" : o.gift = 0 : o.note = ""
@ 4, 13 SAY "Product   : " GET o.product PICTURE "!!!!" LOOKUP (SELECT code, name, price FROM products ORDER BY code)
@ 5, 13 SAY "Quantity  : " GET o.qty PICTURE "999" VALID o.qty >= 1 AND o.qty <= 100 MESSAGE "Quantity must be 1 to 100"
@ 6, 13 SAY "Member    : " GET o.member CHECKBOX
@ 7, 13 SAY "Discount %: " GET o.discount PICTURE "99.99" WHEN o.member = "Y" VALID o.discount <= 20 MESSAGE "Members get at most 20%"
@ 9, 13 SAY "Ship on   : " GET o.ship PICTURE "@D"
@ 10, 13 SAY "Ship to   : " GET o.state LIST "CA,FL,NY,TX,WA"
@ 11, 13 SAY "Phone     : " GET o.phone PICTURE "@R (999) 999-9999"
@ 12, 13 SAY "Gift wrap : " GET o.gift CHECKBOX
@ 13, 13 SAY "Note      : " GET o.note PICTURE "@S40" HINT "Delivery instructions, or anything else about the order"
@ 15, 13 SAY "F1 = help   F2 = list of products or states"
@ 17, 25 BUTTON "Save"
@ 17, 35 BUTTON "Cancel" CANCEL
READ

COLOR 7, 0
CLS
IF BUTTON$ = "Save" THEN
    price = (SELECT price FROM products WHERE code = :o.product)
    total = price * o.qty * (100 - o.discount) / 100
    PRINT "Order:"; o.qty; " x "; o.product; " = "; TRIM$(FORMAT$(total, "$#,##0.00"))
    PRINT "Ship on "; o.ship; " to "; o.state; ", phone "; o.phone;
    IF o.gift THEN PRINT ", gift wrapped" ELSE PRINT
    IF o.note <> "" THEN PRINT "Note: "; o.note
ELSE
    PRINT "Order cancelled."
END IF
REM EXPECT: Order: 3 x B200 = $26.25
REM EXPECT: Ship on 2026-11-15 to NY, phone 5551234567, gift wrapped
REM EXPECT: Note: Leave at the side door
