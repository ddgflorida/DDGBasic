REM Date/time and formatting function fixes, and CARDINAL$ / ORDINAL$.
REM Any failed check raises an error (exit 1).
IF WEEKDAYNAME$(1) <> "Sunday" THEN ERROR 1, "WEEKDAYNAME$(1) = " + WEEKDAYNAME$(1)
IF WEEKDAYNAME$(7) <> "Saturday" THEN ERROR 1, "WEEKDAYNAME$(7) = " + WEEKDAYNAME$(7)
IF WEEKDAYNAME$(WEEKDAY("2024-07-04")) <> "Thursday" THEN ERROR 1, "WEEKDAY/WEEKDAYNAME$ mismatch"

IF HOUR("2024-07-04 13:45:10") <> 13 THEN ERROR 1, "HOUR of a datetime"
IF MINUTE("2024-07-04 13:45:10") <> 45 THEN ERROR 1, "MINUTE of a datetime"
IF SECOND("2024-07-04T13:45:10") <> 10 THEN ERROR 1, "SECOND of an ISO datetime"
IF HOUR("09:05:00") <> 9 THEN ERROR 1, "HOUR of a time"

IF DAYSINMONTH(2, 2024) <> 29 THEN ERROR 1, "DAYSINMONTH(month, year)"
IF DAYSINMONTH(2024, 2) <> 29 THEN ERROR 1, "DAYSINMONTH(year, month)"

IF CARDINAL$(1234) <> "one thousand two hundred thirty-four" THEN ERROR 1, "CARDINAL$(1234) = " + CARDINAL$(1234)
IF CARDINAL$(-5) <> "negative five" THEN ERROR 1, "CARDINAL$(-5)"
IF CARDINAL$(3.14) <> "three point one four" THEN ERROR 1, "CARDINAL$(3.14)"
IF ORDINAL$(21) <> "twenty-first" THEN ERROR 1, "ORDINAL$(21) = " + ORDINAL$(21)
IF ORDINAL$(12) <> "twelfth" THEN ERROR 1, "ORDINAL$(12)"
IF ORDINAL$(100) <> "one hundredth" THEN ERROR 1, "ORDINAL$(100)"

IF FORMAT$(0.256, "0.00%") <> "25.60%" THEN ERROR 1, "FORMAT$ percent = " + FORMAT$(0.256, "0.00%")
IF FORMAT$(42, "### units") <> " 42 units" THEN ERROR 1, "FORMAT$ trailing text = [" + FORMAT$(42, "### units") + "]"
REM FORMAT$: a number wider than a comma mask is grouped in thousands all the way
IF FORMAT$(1168005, "#,##0") <> "1,168,005" THEN ERROR 1, "FORMAT$ grouping: " & FORMAT$(1168005, "#,##0")
IF FORMAT$(-7654321.5, "#,##0.00") <> "-7,654,321.50" THEN ERROR 1, "FORMAT$ negative grouping: " & FORMAT$(-7654321.5, "#,##0.00")
IF FORMAT$(1234567, "##0") <> "1234567" THEN ERROR 1, "FORMAT$ without a comma stays ungrouped"
PRINT "function_fixes: all checks passed"
