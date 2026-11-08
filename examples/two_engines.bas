REM ===================================================================
REM Two engines, one program: SQLite keeps the records, DuckDB analyses them.
REM
REM   SQLite is the system of record: a file, constraints, transactions.
REM   DuckDB is the analyst: columnar, fast, at home with Parquet files.
REM   DDGBasic switches between them with DATABASE ENGINE and moves the data
REM   with its own output formats, so each engine does the job it is best at.
REM ===================================================================
IF FILE_EXISTS("shop_records.db") THEN KILL "shop_records.db"

REM --- 1. SQLite: the records, with rules the database enforces --------------------
DATABASE ENGINE SQLITE
DATABASE OPEN "shop_records.db"
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, region TEXT NOT NULL);
CREATE TABLE orders (id INTEGER PRIMARY KEY,
                     customer_id INTEGER NOT NULL REFERENCES customers(id),
                     placed TEXT NOT NULL,
                     amount REAL NOT NULL CHECK (amount > 0));
INSERT INTO customers (name, region) VALUES
    ('Acme Corp', 'East'), ('Globex', 'West'), ('Initech', 'East'),
    ('Hooli', 'West'), ('Umbrella', 'North'), ('Stark Ltd', 'North');

REM Two thousand orders, written in one transaction (much faster than one by one)
BEGIN TRANSACTION;
FOR i = 1 TO 2000
    customer = 1 + MOD(i * 7, 6)
    placed$ = DATEADD("2025-01-01", MOD(i * 13, 365))
    amount = 20 + MOD(i * 37, 480)
    INSERT INTO orders (customer_id, placed, amount) VALUES (:customer, :placed$, :amount);
NEXT i
COMMIT;
PRINT "SQLite: " & (SELECT COUNT(*) FROM orders) & " orders in shop_records.db"
REM EXPECT: SQLite: 2000 orders in shop_records.db

REM The database refuses bad data; the program checks ERR instead of stopping
REM (the refused statement is also reported on the error output)
SET SQL_FATAL_ERRORS OFF
INSERT INTO orders (customer_id, placed, amount) VALUES (1, '2025-06-01', -50);
IF ERR THEN PRINT "SQLite refused an order: "; ERRMSG$
SET SQL_FATAL_ERRORS ON
REM EXPECT: SQLite refused an order: CHECK constraint failed

REM --- 2. Hand the data to DuckDB as a Parquet file ----------------------------------
SET OUTPUT FILE "orders.parquet" FORMAT PARQUET
SELECT o.id, c.name AS customer, c.region, o.placed, o.amount
  FROM orders o JOIN customers c ON c.id = o.customer_id;
SET OUTPUT CONSOLE

REM --- 3. DuckDB: the analysis ----------------------------------------------------
DATABASE ENGINE DUCKDB
PRINT
PRINT "DuckDB, reading orders.parquet: the median order and the busiest month per region"
SELECT region,
       COUNT(*) AS orders,
       ROUND(median(amount), 2) AS median_order,
       ROUND(SUM(amount), 2) AS revenue,
       strftime(arg_max(month, month_revenue), '%Y-%m') AS best_month
  FROM (SELECT region, amount, date_trunc('month', CAST(placed AS DATE)) AS month,
               SUM(amount) OVER (PARTITION BY region, date_trunc('month', CAST(placed AS DATE))) AS month_revenue
          FROM 'orders.parquet')
 GROUP BY region ORDER BY revenue DESC;

REM The monthly figures go back to SQLite as a CSV file
SET OUTPUT FILE "monthly.csv" FORMAT CSV
SELECT region, strftime(date_trunc('month', CAST(placed AS DATE)), '%Y-%m') AS month,
       ROUND(SUM(amount), 2) AS revenue
  FROM 'orders.parquet' GROUP BY ALL ORDER BY region, month;
SET OUTPUT CONSOLE

REM --- 4. Back to SQLite: keep the results with the records ---------------------------
DATABASE ENGINE SQLITE
DATABASE OPEN "shop_records.db"
CREATE TABLE monthly (region TEXT, month TEXT, revenue REAL);
LOAD CSV "monthly.csv" INTO TABLE monthly OPTIONS "header=true"
PRINT
PRINT "Back in SQLite: " & (SELECT COUNT(*) FROM monthly) & " monthly figures stored next to the orders"
REM EXPECT: monthly figures stored next to the orders

REM A rule in BASIC over the stored figures: each region's strongest quarter
FOR r IN (SELECT DISTINCT region FROM monthly ORDER BY region)
    best = 0 : best_q$ = ""
    FOR q = 1 TO 4
        first$ = "2025-" & RIGHT$("0" & (q * 3 - 2), 2)
        last$ = "2025-" & RIGHT$("0" & (q * 3), 2)
        total = (SELECT COALESCE(SUM(revenue), 0) FROM monthly
                  WHERE region = :r.region AND month BETWEEN :first$ AND :last$)
        IF total > best THEN best = total : best_q$ = "Q" & q
    NEXT q
    PRINT "  " & r.region & ": strongest quarter " & best_q$ & " (" & FORMAT$(best, "#,##0") & ")"
NEXT
REM EXPECT: strongest quarter
