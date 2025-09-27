REM Create a sample CSV file with no header row
OPEN "cities.csv" FOR OUTPUT AS #1
PRINT #1, "New York,USA,8400000"
PRINT #1, "London,UK,8900000"
PRINT #1, "Tokyo,Japan,14000000"
CLOSE #1

REM Load the CSV into a table, explicitly defining fields for the headerless file
LOAD CSV "cities.csv" CREATE TABLE "cities" 
REM LOAD CSV "cities.csv" CREATE TABLE "cities" OPTIONS "fields=[C1] as City,[C2] as Country,[C3] as Population"

REM Display the contents to verify the column names
PRINT "Contents of 'cities' table with explicitly defined column names:"
SELECT * FROM cities;

REM Clean up the temporary file
KILL "cities.csv"
END

