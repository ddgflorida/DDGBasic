REM --- SQLite Database Example ---
REM This program demonstrates creating a table, inserting data (using bind variables),
REM and then querying that data with a FOR...IN loop.

PRINT "--- SQLite Example ---"

REM Create a table for our products
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT,
    price REAL
);

REM Insert some data using variables
LET P_NAME$ = "Laptop Computer"
LET P_PRICE = 1200.50
INSERT INTO products (name, price) VALUES (:P_NAME$, :P_PRICE);

LET P_NAME$ = "Wireless Mouse"
LET P_PRICE = 25.75
INSERT INTO products (name, price) VALUES (:P_NAME$, :P_PRICE);

PRINT "Products in the database:"
PRINT "--------------------------"

REM Use a FOR...IN loop to query the database and print the results
FOR rec IN (SELECT id, name, price FROM products ORDER BY price) 
    PRINT USING "ID: ##  Name: \          \  Price: $#,###.00"; rec.id, rec.name$, rec.price
NEXT

PRINT "--------------------------"
PRINT "Query complete."

END
