CREATE TABLE customers (
    customer_id INTEGER,
    customer_name TEXT,
    last_sale REAL,
    notes TEXT
);
REM Note the header of example.csv is:
REM id,name,amount,Remark
REM The fields option renames the columns, which will then match the CREATE TABLE columns above
LOAD CSV "example.csv" INTO TABLE customers APPEND OPTIONS "header=true,fields=[id] as customer_id,[name] as customer_name,[amount] as last_sale,[remark] as notes,transform=name:proper,notes:trim"
print err,errmsg$
' Display the cleaned data to verify the transformations worked
PRINT "--- Cleaned Customer Data ---"
SELECT * FROM customers;
