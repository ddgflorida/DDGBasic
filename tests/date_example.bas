REM --- Date and Time Functions Example ---
REM This program demonstrates the various functions for handling dates.

PRINT "--- Date Functions Example ---"

PRINT "Current System Date:", DATE$
PRINT "Current System Time:", TIME$
PRINT

LET START_DATE$ = "2025-12-15"
PRINT "Start Date:", START_DATE$
PRINT

REM --- Calculations ---
LET FUTURE_DATE$ = DATEADD(START_DATE$, 90)
PRINT "Start date + 90 days:", FUTURE_DATE$

LET DAYS_BETWEEN = DATEDIFF(FUTURE_DATE$, START_DATE$)
PRINT "Days between dates:";FUTURE_DATE$; " and ";START_DATE$; ":", DAYS_BETWEEN
PRINT

REM --- Component Extraction ---
PRINT "Year of start date:", YEAR(START_DATE$)
PRINT "Month of start date:", MONTH(START_DATE$)
PRINT "Day of start date:", DAY(START_DATE$)
PRINT "Weekday of start date (1=Sun):", WEEKDAY(START_DATE$)
PRINT

REM --- Formatting ---
PRINT "Formatted as MM/DD/YYYY:", FORMATDATE$(START_DATE$, "MM/DD/YYYY")
PRINT "Formatted as DD-MM-YY:", FORMATDATE$(START_DATE$, "DD-MM-YY")

END
