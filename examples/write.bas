' Write CSV to console
WRITE "Name", "Age", "City"
WRITE "Alice", 30, "New York"
WRITE "Bob", 25, "Los Angeles"

CREATE TABLE products (id integer,name text,price real);
INSERT INTO products VALUES(1,'WOW Brand Soap',8.23);
' Write CSV to file
PRINT "Writing to export.csv"
OPEN "export.csv" FOR OUTPUT AS #1
WRITE #1, "ID", "Product", "Price"
FOR row IN (SELECT * FROM products)
    WRITE #1, row.id, row.name, row.price
NEXT
CLOSE #1
REM
PRINT "CSV Created:","export.csv"
