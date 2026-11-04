CREATE TABLE customers (
    customer_id INTEGER,
    customer_name TEXT,
    last_sale REAL,
    notes TEXT
);
REM Note the header of example.csv is:
REM id,name,amount,Remark
REM The fields option renames the columns, which will then match the CREATE TABLE columns above
LOAD CSV "example.csv" INTO TABLE customers APPEND OPTIONS "header=true, fields=id:customer_id,name:customer_name,amount:last_sale,remark:notes, transform=customer_name:proper;notes:trim"
print err,errmsg$
REM Display the cleaned data to verify the transformations worked
PRINT "--- Cleaned Customer Data ---"
SELECT * FROM customers;
