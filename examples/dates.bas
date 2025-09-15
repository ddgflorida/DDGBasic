' Get current date and time
PRINT "Today is "; DATE$
PRINT "The time is "; TIME$

' Date calculations
start_date$ = "2024-01-01"
end_date$ = DATEADD(start_date$, 90)  ' Add 90 days
PRINT "Project ends on "; end_date$

days_remaining = DATEDIFF(end_date$, DATE$)
PRINT "Days remaining: "; days_remaining

' Date components
year = YEAR(DATE$)
month = MONTH(DATE$)
day = DAY(DATE$)
weekday = WEEKDAY(DATE$)

IF weekday = 1 OR weekday = 7 THEN
    PRINT "It's the weekend!"
END IF

' Format dates (Format codes: YYYY=year, MM=month, DD=day)
us_format$ = FORMATDATE$(DATE$, "MM/DD/YYYY")
euro_format$ = FORMATDATE$(DATE$, "DD.MM.YYYY")
iso_format$ = FORMATDATE$(DATE$, "YYYY-MM-DD")
PRINT "US Format: "; us_format$
PRINT "European Format: "; euro_format$
PRINT "ISO Format: "; iso_format$

' Calculate age
birthdate$ = "1990-05-15"
age_days = DATEDIFF(DATE$, birthdate$)
age_years = INT(age_days / 365.25)
PRINT "Age: "; age_years; " years"

' Find next Monday
today$ = DATE$
day_of_week = WEEKDAY(today$)
IF day_of_week = 1 THEN
    ' Sunday - add 1 day
    next_monday$ = DATEADD(today$, 1)
ELSE 
    IF day_of_week = 2 THEN
    ' Already Monday - add 7 days
    next_monday$ = DATEADD(today$, 7)
    ELSE
        ' Tuesday-Saturday - calculate days to add
        days_to_add = 9 - day_of_week
        next_monday$ = DATEADD(today$, days_to_add)
    END IF
END IF
PRINT "Next Monday: "; next_monday$