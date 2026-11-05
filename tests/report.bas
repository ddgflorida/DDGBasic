REM REPORT: grouped reports with subtotals, totals, FORMAT masks, pages and destinations.
REM Failed checks raise errors.
DATABASE OPEN ":memory:"
CREATE TABLE sales (region TEXT, customer TEXT, qty INTEGER, amount REAL);
INSERT INTO sales VALUES ('East', 'ACME', 3, 300), ('East', 'GLOBEX', 1, 50), ('West', 'HOOLI', 6, 804), ('West', 'INITECH', 2, 80.5);
REPORT (SELECT region, customer, qty, amount FROM sales ORDER BY region, customer) _
    TITLE "Sales by region" GROUP BY region TOTAL qty, amount FORMAT amount "#,##0.00" INTO r$
lines = SPLIT(r$, CHR$(10))
IF LEFT$(lines(0), 15) <> "Sales by region" THEN ERROR 1, "title line: " & lines(0)
IF lines(2) <> "customer  qty   amount" THEN ERROR 1, "headings: [" & lines(2) & "]"
IF lines(4) <> "region: East" THEN ERROR 1, "group heading: " & lines(4)
IF lines(5) <> "ACME        3   300.00" THEN ERROR 1, "row: [" & lines(5) & "]"
IF lines(8) <> "East (2)    4   350.00" THEN ERROR 1, "subtotal: [" & lines(8) & "]"
IF lines(17) <> "Total (4)  12 1,234.50" THEN ERROR 1, "grand total: [" & lines(17) & "]"

REM Pages in a file are separated by form feeds, and each repeats the headings
REPORT (SELECT region AS Region, customer, amount FROM sales ORDER BY 1, 2) TOTAL amount PAGE 8 TO FILE "report_out.txt"
READ FILE "report_out.txt" INTO f$
IF INSTR(f$, CHR$(12)) = 0 THEN ERROR 1, "PAGE should put a form feed between pages"
IF INSTR(f$, "Page 2") = 0 THEN ERROR 1, "the second page should be numbered"
IF INSTR(f$, "Region customer") = 0 THEN ERROR 1, "AS alias as the heading"

REM No groups and no totals: a row count at the end
REPORT (SELECT customer FROM sales ORDER BY customer) INTO plain$
IF INSTR(plain$, "(4 rows)") = 0 THEN ERROR 1, "row count footer"

REM TO VIEW shows the report in the viewer. Keys: q
REPORT (SELECT customer, qty FROM sales ORDER BY customer) TOTAL qty TO VIEW
IF LASTKEY$ <> "q" THEN ERROR 1, "TO VIEW"

ON ERROR GOTO bad_column
REPORT (SELECT region, amount FROM sales) GROUP BY nosuch
ERROR 1, "an unknown column should be an error"
bad_column:
IF INSTR(ERRMSG$, "no column 'nosuch'") = 0 THEN ERROR 1, "message: " & ERRMSG$
RESUME done
done:
ON ERROR GOTO 0
report = 5
IF report <> 5 THEN ERROR 1, "report as a variable name"
REPORT (SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY region) TOTAL total
REM EXPECT: Total (2)
PRINT "report: all checks passed"
REM EXPECT: report: all checks passed
