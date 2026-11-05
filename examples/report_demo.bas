REM Report demo: REPORT with nested groups, subtotals and totals, on the screen,
REM in the viewer (arrows scroll, / finds, q closes) and in a file with pages.
DATABASE OPEN ":memory:"
CREATE TABLE sales (region TEXT, rep TEXT, month TEXT, amount REAL);
INSERT INTO sales VALUES
    ('East', 'Ann', '2026-01', 1200), ('East', 'Ann', '2026-02', 950.5), ('East', 'Bob', '2026-01', 400),
    ('East', 'Bob', '2026-02', 610.25), ('West', 'Cy', '2026-01', 2300), ('West', 'Cy', '2026-02', 1800),
    ('West', 'Di', '2026-01', 75), ('West', 'Di', '2026-02', 300);

REM 1. On the screen, grouped by region and rep
REPORT (SELECT region, rep, month, amount FROM sales ORDER BY region, rep, month) _
    TITLE "Sales by region and rep" GROUP BY region, rep TOTAL amount FORMAT amount "$#,##0.00"

REM 2. In the viewer
REPORT (SELECT region, month, SUM(amount) AS amount FROM sales GROUP BY region, month ORDER BY region, month) _
    TITLE "Monthly sales" GROUP BY region TOTAL amount FORMAT amount "$#,##0.00" TO VIEW

REM 3. In a file, 20 lines to a page (pages are separated by form feeds)
REPORT (SELECT region, rep, month, amount FROM sales ORDER BY region, rep, month) _
    TITLE "Sales" GROUP BY region TOTAL amount FORMAT amount "$#,##0.00" PAGE 20 TO FILE "sales_report.txt"
PRINT "Saved sales_report.txt"
REM EXPECT: Total (8)
REM EXPECT: Saved sales_report.txt
