REM ===================================================================
REM DuckDB analytics: half a million rows, queried straight from Parquet
REM and CSV files, with window functions, and BASIC logic on the results.
REM
REM   DuckDB is a fast analytical database. DDGBasic gives it a program
REM   around it: variables and rules, loops over results, timings, files.
REM ===================================================================
DATABASE ENGINE DUCKDB
DATABASE OPEN ":memory:"

REM --- Half a million sales, made in one SQL statement ------------------------
start = TIMER
CREATE TABLE sales AS
SELECT i AS id,
       ['North', 'South', 'East', 'West'][1 + (i * 7) % 4] AS region,
       ['Widget', 'Gadget', 'Gizmo', 'Sprocket', 'Flange'][1 + (i * 13) % 5] AS product,
       DATE '2025-01-01' + CAST((i * 37) % 365 AS INTEGER) AS sold_on,
       1 + (i * 11) % 9 AS qty,
       ROUND(2 + ((i * 17) % 400) / 10.0, 2) AS price
  FROM range(500000) t(i);
rows = (SELECT COUNT(*) FROM sales)
PRINT "Made "; FORMAT$(rows, "#,##0"); " sales in "; FORMAT$(TIMER - start, "0.00"); " s"
REM EXPECT: Made 500,000 sales

REM --- Write them as Parquet and CSV, then query the files directly ----------------
SET OUTPUT FILE "sales.parquet" FORMAT PARQUET
SELECT * FROM sales;
SET OUTPUT FILE "sales.csv" FORMAT CSV
SELECT * FROM sales;
SET OUTPUT CONSOLE

start = TIMER
PRINT
PRINT "Revenue by region, read straight from sales.parquet:"
SELECT region, COUNT(*) AS sales, ROUND(SUM(qty * price), 2) AS revenue
  FROM 'sales.parquet' GROUP BY region ORDER BY revenue DESC;
PRINT "  ("; FORMAT$(TIMER - start, "0.000"); " s)"
REM EXPECT: Revenue by region, read straight from sales.parquet:

start = TIMER
csv_rows = (SELECT COUNT(*) FROM read_csv_auto('sales.csv'))
PRINT "The CSV file has "; FORMAT$(csv_rows, "#,##0"); " rows, counted in "; FORMAT$(TIMER - start, "0.000"); " s"
REM EXPECT: The CSV file has 500,000 rows

REM --- Window functions: each region's best product, and a running total ------------
PRINT
PRINT "Best-selling product in each region:"
SELECT region, product, revenue FROM (
    SELECT region, product, ROUND(SUM(qty * price), 2) AS revenue,
           RANK() OVER (PARTITION BY region ORDER BY SUM(qty * price) DESC) AS place
      FROM sales GROUP BY region, product)
 WHERE place = 1 ORDER BY region;

REM --- BASIC rules on the results ---------------------------------------------------
REM Each region has its own monthly target. A loop over the monthly totals (with a
REM running total from a window function) flags the months under target and keeps a
REM count per region in a hash, which plain SQL would need a separate table for.
DIM targets AS HASH
targets("North") = 1140000 : targets("South") = 1150000
targets("East") = 1150000 : targets("West") = 1145000
DIM misses AS HASH
PRINT
PRINT "Months under target (first three per region):"
FOR m IN (SELECT region, strftime(month, '%Y-%m') AS month, revenue,
                 SUM(revenue) OVER (PARTITION BY region ORDER BY month) AS to_date
            FROM (SELECT region, date_trunc('month', sold_on) AS month,
                         ROUND(SUM(qty * price), 2) AS revenue
                    FROM sales GROUP BY region, month)
           ORDER BY region, month)
    IF m.revenue < targets(m.region) THEN
        IF HASH_EXISTS(misses, m.region) THEN misses(m.region) = misses(m.region) + 1 ELSE misses(m.region) = 1
        IF misses(m.region) <= 3 THEN
            PRINT "  " & m.region & " " & m.month & ": " & FORMAT$(m.revenue, "#,##0") & _
                  " (target " & FORMAT$(targets(m.region), "#,##0") & ", year to date " & FORMAT$(m.to_date, "#,##0") & ")"
        END IF
    END IF
NEXT
PRINT
FOR EACH region$ IN HASH misses
    PRINT "  " & region$ & ": " & misses(region$) & " months under target"
NEXT
REM EXPECT: months under target
