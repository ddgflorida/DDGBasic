REM ===================================================================
REM ETL pipeline: a messy export becomes a clean table, a summary and
REM three output files, in one short program.
REM
REM   1. LOAD the raw CSV. Your own BASIC functions clean every cell as it
REM      loads (TRANSFORM ... WITH) and drop rows that fail a check
REM      (VALIDATE ... WITH). No staging table, no second pass.
REM   2. BASIC rules over SQL results: FOR row IN (SELECT ...) loops apply
REM      logic that is awkward in SQL (tiers, flags), writing back with
REM      bind variables (:name).
REM   3. SQL does what it is best at: grouping and totals.
REM   4. The same queries go to JSON, Excel and a grouped text report.
REM ===================================================================

REM --- The raw export, as it might arrive: odd spacing, mixed phone formats,
REM     amounts with $ and commas, a bad e-mail, a blank amount, a repeat order
OPEN "etl_raw.csv" FOR OUTPUT AS #1
PRINT #1, "order_id,customer,email,phone,state,amount"
PRINT #1, "1001,  ann lee ,ann@example.com,(555) 123-4567,fl,""$1,250.00"""
PRINT #1, "1002,BOB STONE,bob@example,555.987.6543,NY,320"
PRINT #1, "1003,carla diaz,carla@example.com,5552223333,ny,""$2,100.50"""
PRINT #1, "1004,  Dan Ito,dan@example.com,555-444-1212,CA,"
PRINT #1, "1005,ann lee,ann@example.com,555 123 4567,FL,$75.25"
PRINT #1, "1006,Eve Park,eve@example.com,+1 555 777 8888,ca,980"
PRINT #1, "1007,frank moss,frank@example.com,(555)321-0000,tx,""$4,800"""
PRINT #1, "1003,carla diaz,carla@example.com,5552223333,ny,""$2,100.50"""
CLOSE #1

REM --- Cleaning functions: called by LOAD for every cell or row ---------------
FUNCTION normalize_phone$(p$)
    REM Keep the last ten digits and show them as (555) 123-4567
    digits$ = ""
    FOR i = 1 TO LEN(p$)
        c$ = MID$(p$, i, 1)
        REM & joins text; + would add "5" + "5" as numbers
        IF c$ >= "0" AND c$ <= "9" THEN digits$ = digits$ & c$
    NEXT i
    IF LEN(digits$) > 10 THEN digits$ = RIGHT$(digits$, 10)
    IF LEN(digits$) <> 10 THEN
        normalize_phone$ = ""
    ELSE
        normalize_phone$ = "(" & LEFT$(digits$, 3) & ") " & MID$(digits$, 4, 3) & "-" & RIGHT$(digits$, 4)
    END IF
END FUNCTION

FUNCTION clean_amount(v$)
    REM "$1,250.00" -> 1250
    clean_amount = VAL(REPLACE$(REPLACE$(TRIM$(v$), "$", ""), ",", ""))
END FUNCTION

FUNCTION has_amount(v)
    REM VALIDATE sees the cleaned value: an empty amount has become 0
    has_amount = v > 0
END FUNCTION

FUNCTION tidy(r)
    REM A whole row at once: proper-case names, upper-case states
    r("customer") = PROPER$(TRIM$(r("customer")))
    r("state") = UCASE$(TRIM$(r("state")))
    tidy = r
END FUNCTION

REM --- 1. Load into a typed table, cleaning as we go --------------------------
DATABASE OPEN ":memory:"
CREATE TABLE orders (order_id INTEGER, customer TEXT, email TEXT, phone TEXT, state TEXT, amount REAL);
LOAD CSV "etl_raw.csv" INTO TABLE orders OPTIONS "header=true" _
    TRANSFORM phone WITH normalize_phone$ _
    VALIDATE amount WITH has_amount _
    TRANSFORM amount WITH clean_amount _
    TRANSFORM ROW WITH tidy
REM EXPECT: 7 records loaded into table orders

REM --- 2. BASIC rules over SQL results --------------------------------------
PRINT
PRINT "Checks"
FOR d IN (SELECT order_id, COUNT(*) AS copies FROM orders GROUP BY order_id HAVING COUNT(*) > 1)
    PRINT "  order " & d.order_id & " appears " & d.copies & " times: keeping one"
    DELETE FROM orders WHERE rowid NOT IN (SELECT MIN(rowid) FROM orders WHERE order_id = :d.order_id)
        AND order_id = :d.order_id;
NEXT
FOR b IN (SELECT order_id, email FROM orders WHERE email NOT LIKE '%@%.%')
    PRINT "  order " & b.order_id & ": suspicious e-mail " & b.email
NEXT
REM EXPECT: order 1003 appears 2 times: keeping one
REM EXPECT: order 1002: suspicious e-mail bob@example

REM A customer tier from their total spend: the kind of rule people bury in a CASE,
REM written as plain IFs and saved back with bind variables
CREATE TABLE tiers (customer TEXT PRIMARY KEY, spent REAL, tier TEXT);
FOR c IN (SELECT customer, SUM(amount) AS spent FROM orders GROUP BY customer)
    IF c.spent >= 2000 THEN
        tier$ = "Gold"
    ELSEIF c.spent >= 500 THEN
        tier$ = "Silver"
    ELSE
        tier$ = "Bronze"
    END IF
    INSERT INTO tiers VALUES (:c.customer, :c.spent, :tier$);
NEXT

REM --- 3. SQL for the totals --------------------------------------------------
PRINT
PRINT "Customers by tier"
SELECT tier, COUNT(*) AS customers, ROUND(SUM(spent), 2) AS spent
  FROM tiers GROUP BY tier ORDER BY spent DESC;

REM --- 4. The same data three ways ----------------------------------------------
SET OUTPUT FILE "etl_summary.json" FORMAT JSON
SELECT o.state, o.customer, o.phone, o.amount, t.tier
  FROM orders o JOIN tiers t ON t.customer = o.customer ORDER BY o.state, o.customer;
SET OUTPUT FILE "etl_summary.xlsx" FORMAT EXCEL
SELECT state, COUNT(*) AS orders, SUM(amount) AS amount FROM orders GROUP BY state ORDER BY state;
SET OUTPUT CONSOLE
REM EXPECT: 6 rows written to etl_summary.json

PRINT
REPORT (SELECT state, customer, amount FROM orders ORDER BY state, customer) _
    TITLE "Orders by state" GROUP BY state TOTAL amount FORMAT amount "#,##0.00"
REM EXPECT: Total (6)
